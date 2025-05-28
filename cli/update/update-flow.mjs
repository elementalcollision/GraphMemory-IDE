import chalk from 'chalk';
import { SignatureVerifier } from './signature-verifier.mjs';
import { UpdateStateManager } from './state-manager.mjs';
import { DatabaseMigrator } from './database-migrator.mjs';
import { ContainerUpdater } from './container-updater.mjs';

/**
 * UpdateFlow - Main orchestrator for CLI update operations
 * Integrates all update components with comprehensive error handling
 * Features:
 * - Complete update orchestration
 * - Signature verification before any operations
 * - Atomic state management with rollback
 * - Database migration with backup/restore
 * - Blue-Green or Rolling container deployment
 * - Health monitoring and validation
 * - Comprehensive error handling and recovery
 */
export class UpdateFlow {
  constructor(options = {}) {
    this.verbose = options.verbose || false;
    this.dryRun = options.dryRun || false;
    this.strategy = options.strategy || 'blue-green';
    this.verifySignatures = options.verifySignatures !== false;
    this.backupDatabase = options.backupDatabase !== false;
    
    // Initialize components
    this.signatureVerifier = new SignatureVerifier({
      verbose: this.verbose,
      ...options.signatureVerifier
    });
    
    this.stateManager = new UpdateStateManager({
      verbose: this.verbose,
      ...options.stateManager
    });
    
    this.databaseMigrator = new DatabaseMigrator({
      verbose: this.verbose,
      ...options.databaseMigrator
    });
    
    this.containerUpdater = new ContainerUpdater({
      verbose: this.verbose,
      strategy: this.strategy,
      ...options.containerUpdater
    });
    
    this.updateState = null;
    this.lockId = null;
  }

  /**
   * Execute complete update flow
   * @param {Object} updatePlan - Complete update plan
   * @param {Object} options - Execution options
   * @returns {Promise<Object>} - Update result
   */
  async execute(updatePlan, options = {}) {
    const startTime = Date.now();
    
    try {
      this._log(chalk.cyan.bold('🚀 Starting GraphMemory-IDE Update Flow'));
      this._log(`Strategy: ${this.strategy.toUpperCase()}`);
      this._log(`Dry Run: ${this.dryRun ? 'YES' : 'NO'}`);
      this._log(`Verify Signatures: ${this.verifySignatures ? 'YES' : 'NO'}`);
      
      if (this.dryRun) {
        return await this._executeDryRun(updatePlan, options);
      }
      
      // Phase 1: Pre-Update Validation
      await this._executePhase1(updatePlan, options);
      
      // Phase 2: Update Execution
      const updateResult = await this._executePhase2(updatePlan, options);
      
      // Phase 3: Post-Update Validation
      await this._executePhase3(updateResult, options);
      
      const duration = Date.now() - startTime;
      this._log(chalk.green.bold(`✅ Update completed successfully in ${duration}ms`));
      
      return {
        success: true,
        duration,
        strategy: this.strategy,
        phases: {
          validation: true,
          execution: true,
          postValidation: true
        },
        result: updateResult
      };
      
    } catch (error) {
      this._logError('Update flow failed:', error);
      
      // Attempt comprehensive rollback
      await this._executeRollback(error);
      
      throw new Error(`Update failed: ${error.message}`);
      
    } finally {
      // Cleanup resources
      await this._cleanup();
    }
  }

  /**
   * Execute dry run to show what would be updated
   * @private
   */
  async _executeDryRun(updatePlan, options) {
    this._log(chalk.yellow.bold('🔍 Executing Dry Run'));
    
    const dryRunResult = {
      wouldUpdate: true,
      phases: {},
      estimatedDuration: 0
    };
    
    // Simulate Phase 1: Validation
    this._log(chalk.blue('Phase 1: Pre-Update Validation (Simulated)'));
    
    if (this.verifySignatures && updatePlan.images) {
      this._log(`  Would verify signatures for ${updatePlan.images.length} images`);
      dryRunResult.phases.signatureVerification = {
        images: updatePlan.images.map(img => `${img.name}:${img.tag}`)
      };
    }
    
    this._log('  Would acquire update lock');
    this._log('  Would validate current system health');
    
    if (this.backupDatabase) {
      this._log('  Would create database backup');
      dryRunResult.phases.databaseBackup = { wouldCreate: true };
    }
    
    // Simulate Phase 2: Execution
    this._log(chalk.blue('Phase 2: Update Execution (Simulated)'));
    
    if (updatePlan.images) {
      this._log(`  Would pull ${updatePlan.images.length} new images`);
      dryRunResult.phases.imagePull = {
        images: updatePlan.images.map(img => `${img.name}:${img.tag}`)
      };
    }
    
    if (updatePlan.schemaChanges) {
      this._log(`  Would apply ${updatePlan.schemaChanges.length} schema changes`);
      dryRunResult.phases.schemaMigration = {
        changes: updatePlan.schemaChanges
      };
    }
    
    this._log(`  Would deploy using ${this.strategy.toUpperCase()} strategy`);
    dryRunResult.phases.containerUpdate = {
      strategy: this.strategy,
      services: updatePlan.services || []
    };
    
    // Simulate Phase 3: Post-Validation
    this._log(chalk.blue('Phase 3: Post-Update Validation (Simulated)'));
    this._log('  Would run health checks');
    this._log('  Would validate functionality');
    this._log('  Would update state');
    
    dryRunResult.estimatedDuration = this._estimateUpdateDuration(updatePlan);
    
    this._log(chalk.green(`✅ Dry run completed. Estimated duration: ${dryRunResult.estimatedDuration}ms`));
    
    return dryRunResult;
  }

  /**
   * Phase 1: Pre-Update Validation
   * @private
   */
  async _executePhase1(updatePlan, options) {
    this._log(chalk.blue.bold('📋 Phase 1: Pre-Update Validation'));
    
    // Step 1: Acquire update lock
    this._log('Step 1: Acquiring update lock...');
    this.lockId = await this.stateManager.acquireLock();
    
    // Step 2: Verify signatures
    if (this.verifySignatures && updatePlan.images) {
      this._log('Step 2: Verifying image signatures...');
      const verificationResults = await this.signatureVerifier.verifyMultipleImages(
        updatePlan.images.map(img => `${img.name}:${img.tag}`),
        options.signatureOptions
      );
      
      // Check for verification failures
      const failures = Object.entries(verificationResults)
        .filter(([_, result]) => !result.verified);
      
      if (failures.length > 0) {
        throw new Error(`Signature verification failed for: ${failures.map(([img]) => img).join(', ')}`);
      }
      
      this._log(`✅ All ${Object.keys(verificationResults).length} signatures verified`);
    }
    
    // Step 3: Health check current system
    this._log('Step 3: Validating current system health...');
    const currentHealth = await this.containerUpdater.getContainerStatus();
    
    if (currentHealth.health === 'unhealthy') {
      throw new Error('Current system is unhealthy. Cannot proceed with update.');
    }
    
    // Step 4: Create database backup
    if (this.backupDatabase) {
      this._log('Step 4: Creating database backup...');
      const backupResult = await this.databaseMigrator.createBackup({
        reason: 'pre-update-backup'
      });
      
      this.updateState = {
        currentPhase: 'validation',
        progress: 25,
        startTime: new Date().toISOString(),
        backupId: backupResult.backupId,
        originalHealth: currentHealth
      };
    }
    
    // Step 5: Save initial state
    this._log('Step 5: Saving initial state...');
    await this.stateManager.saveState(this.updateState, this.lockId);
    
    this._log(chalk.green('✅ Phase 1 completed successfully'));
  }

  /**
   * Phase 2: Update Execution
   * @private
   */
  async _executePhase2(updatePlan, options) {
    this._log(chalk.blue.bold('⚙️ Phase 2: Update Execution'));
    
    // Update state
    this.updateState.currentPhase = 'execution';
    this.updateState.progress = 50;
    await this.stateManager.saveState(this.updateState, this.lockId);
    
    let updateResult = {};
    
    // Step 1: Database migration (if needed)
    if (updatePlan.schemaChanges && updatePlan.schemaChanges.length > 0) {
      this._log('Step 1: Migrating database schema...');
      
      const migrationResult = await this.databaseMigrator.migrateSchema({
        changes: updatePlan.schemaChanges,
        version: updatePlan.schemaVersion
      });
      
      updateResult.schemaMigration = migrationResult;
      this._log('✅ Schema migration completed');
    }
    
    // Step 2: Container update
    this._log(`Step 2: Updating containers using ${this.strategy.toUpperCase()} strategy...`);
    
    if (this.strategy === 'blue-green') {
      updateResult.containerUpdate = await this.containerUpdater.updateWithBlueGreen(
        updatePlan,
        options.containerOptions
      );
    } else if (this.strategy === 'rolling') {
      updateResult.containerUpdate = await this.containerUpdater.updateWithRolling(
        updatePlan,
        options.containerOptions
      );
    } else {
      throw new Error(`Unknown update strategy: ${this.strategy}`);
    }
    
    this._log('✅ Container update completed');
    
    // Update state with results
    this.updateState.updateResult = updateResult;
    this.updateState.progress = 75;
    await this.stateManager.saveState(this.updateState, this.lockId);
    
    return updateResult;
  }

  /**
   * Phase 3: Post-Update Validation
   * @private
   */
  async _executePhase3(updateResult, options) {
    this._log(chalk.blue.bold('✅ Phase 3: Post-Update Validation'));
    
    // Update state
    this.updateState.currentPhase = 'validation';
    this.updateState.progress = 90;
    await this.stateManager.saveState(this.updateState, this.lockId);
    
    // Step 1: System health check
    this._log('Step 1: Running system health checks...');
    const postUpdateHealth = await this.containerUpdater.getContainerStatus();
    
    if (postUpdateHealth.health === 'unhealthy') {
      throw new Error('Post-update health check failed');
    }
    
    // Step 2: Database health check
    this._log('Step 2: Validating database health...');
    const dbHealth = await this.databaseMigrator.getHealthStatus();
    
    if (!dbHealth.databaseAccessible) {
      throw new Error('Database is not accessible after update');
    }
    
    // Step 3: Functional validation
    this._log('Step 3: Running functional validation...');
    await this._runFunctionalTests(options);
    
    // Step 4: Update final state
    this._log('Step 4: Updating final state...');
    this.updateState.currentPhase = 'completed';
    this.updateState.progress = 100;
    this.updateState.completedAt = new Date().toISOString();
    this.updateState.finalHealth = postUpdateHealth;
    
    await this.stateManager.saveState(this.updateState, this.lockId);
    
    this._log(chalk.green('✅ Phase 3 completed successfully'));
  }

  /**
   * Execute comprehensive rollback
   * @private
   */
  async _executeRollback(error) {
    try {
      this._log(chalk.red.bold('🔄 Executing Rollback'));
      
      if (!this.updateState) {
        this._log('No update state found, skipping rollback');
        return;
      }
      
      // Rollback containers
      if (this.updateState.updateResult?.containerUpdate) {
        this._log('Rolling back container changes...');
        await this.containerUpdater.rollbackToPrevious(
          this.updateState.updateResult.containerUpdate
        );
      }
      
      // Rollback database
      if (this.updateState.backupId) {
        this._log('Rolling back database changes...');
        await this.databaseMigrator.rollbackDatabase(this.updateState.backupId);
      }
      
      // Update state to reflect rollback
      this.updateState.currentPhase = 'rolled-back';
      this.updateState.rollbackReason = error.message;
      this.updateState.rolledBackAt = new Date().toISOString();
      
      if (this.lockId) {
        await this.stateManager.saveState(this.updateState, this.lockId);
      }
      
      this._log(chalk.yellow('⚠️ Rollback completed'));
      
    } catch (rollbackError) {
      this._logError('Rollback failed:', rollbackError);
    }
  }

  /**
   * Cleanup resources
   * @private
   */
  async _cleanup() {
    try {
      if (this.lockId) {
        await this.stateManager.releaseLock(this.lockId);
        this.lockId = null;
      }
      
      // Cleanup state manager
      await this.stateManager.cleanup();
      
    } catch (error) {
      this._logError('Cleanup failed:', error);
    }
  }

  /**
   * Run functional tests
   * @private
   */
  async _runFunctionalTests(options) {
    // Basic functional tests
    // In a real implementation, this would run comprehensive tests
    
    this._log('  Running basic connectivity tests...');
    
    // Test MCP server endpoint
    try {
      const fetch = (await import('node-fetch')).default;
      const response = await fetch('http://localhost:8080/health', { timeout: 5000 });
      
      if (!response.ok) {
        throw new Error(`MCP server health check failed: ${response.status}`);
      }
      
      this._log('  ✅ MCP server connectivity test passed');
    } catch (error) {
      throw new Error(`MCP server test failed: ${error.message}`);
    }
    
    // Additional tests would go here
    this._log('  ✅ All functional tests passed');
  }

  /**
   * Estimate update duration
   * @private
   */
  _estimateUpdateDuration(updatePlan) {
    let duration = 30000; // Base 30 seconds
    
    if (updatePlan.images) {
      duration += updatePlan.images.length * 15000; // 15s per image
    }
    
    if (updatePlan.schemaChanges) {
      duration += updatePlan.schemaChanges.length * 10000; // 10s per schema change
    }
    
    if (this.strategy === 'blue-green') {
      duration += 60000; // Additional 1 minute for Blue-Green
    }
    
    return duration;
  }

  /**
   * Get current update progress
   * @returns {Promise<Object>} - Progress information
   */
  async getProgress() {
    try {
      return await this.stateManager.getProgress();
    } catch (error) {
      return { error: error.message };
    }
  }

  /**
   * Cancel ongoing update
   * @returns {Promise<Object>} - Cancellation result
   */
  async cancel() {
    try {
      this._log(chalk.yellow.bold('🛑 Cancelling update...'));
      
      if (this.updateState) {
        await this._executeRollback(new Error('Update cancelled by user'));
      }
      
      return { cancelled: true };
      
    } catch (error) {
      this._logError('Failed to cancel update:', error);
      throw error;
    }
  }

  /**
   * Logging utility
   * @private
   */
  _log(message) {
    if (this.verbose) {
      console.log(chalk.magenta('[UpdateFlow]'), message);
    }
  }

  /**
   * Error logging utility
   * @private
   */
  _logError(message, error) {
    if (this.verbose) {
      console.error(chalk.red('[UpdateFlow]'), message, error);
    }
  }
}

export default UpdateFlow; 