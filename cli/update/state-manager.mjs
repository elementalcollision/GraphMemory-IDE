import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { constants } from 'node:fs';
import lockfile from 'proper-lockfile';
import { readFile as atomicReadFile, writeFile as atomicWriteFile } from 'atomically';
import chalk from 'chalk';

/**
 * UpdateStateManager - Thread-safe state management for CLI updates
 * Implements atomic operations with file locking to prevent race conditions
 * Features:
 * - Atomic file read/write operations
 * - Process-level locking to prevent concurrent updates
 * - State persistence with rollback information
 * - Timeout and retry logic
 * - Comprehensive error handling
 */
export class UpdateStateManager {
  constructor(options = {}) {
    this.baseDir = options.baseDir || process.cwd();
    this.lockFile = join(this.baseDir, '.graphmemory-update.lock');
    this.stateFile = join(this.baseDir, '.graphmemory-state.json');
    this.backupDir = join(this.baseDir, '.graphmemory-backups');
    this.lockTimeout = options.lockTimeout || 60000; // 1 minute
    this.retryDelay = options.retryDelay || 1000; // 1 second
    this.maxRetries = options.maxRetries || 3;
    this.verbose = options.verbose || false;
    this.currentLock = null;
  }

  /**
   * Acquire exclusive lock for update operations
   * @param {Object} options - Lock options
   * @returns {Promise<string>} - Lock ID
   */
  async acquireLock(options = {}) {
    const lockOptions = {
      stale: this.lockTimeout,
      retries: {
        retries: this.maxRetries,
        factor: 2,
        minTimeout: this.retryDelay,
        maxTimeout: this.lockTimeout / 4
      },
      ...options
    };

    try {
      this._log('Acquiring update lock...');
      
      // Ensure lock directory exists
      await this._ensureDirectory(dirname(this.lockFile));
      
      // Acquire lock
      const release = await lockfile.lock(this.lockFile, lockOptions);
      
      const lockId = this._generateLockId();
      this.currentLock = {
        id: lockId,
        release,
        acquiredAt: new Date().toISOString(),
        pid: process.pid
      };
      
      this._log(`Lock acquired: ${lockId}`);
      return lockId;
      
    } catch (error) {
      this._logError('Failed to acquire lock:', error);
      throw new Error(`Unable to acquire update lock: ${error.message}`);
    }
  }

  /**
   * Release the current lock
   * @param {string} lockId - Lock ID to verify ownership
   */
  async releaseLock(lockId) {
    try {
      if (!this.currentLock) {
        this._log('No active lock to release');
        return;
      }
      
      if (this.currentLock.id !== lockId) {
        throw new Error(`Lock ID mismatch. Expected: ${this.currentLock.id}, Got: ${lockId}`);
      }
      
      this._log(`Releasing lock: ${lockId}`);
      await this.currentLock.release();
      this.currentLock = null;
      this._log('Lock released successfully');
      
    } catch (error) {
      this._logError('Failed to release lock:', error);
      throw error;
    }
  }

  /**
   * Save state atomically with backup
   * @param {Object} state - State object to save
   * @param {string} lockId - Lock ID for verification
   */
  async saveState(state, lockId) {
    this._verifyLock(lockId);
    
    try {
      this._log('Saving state atomically...');
      
      // Ensure state directory exists
      await this._ensureDirectory(dirname(this.stateFile));
      
      // Add metadata
      const stateWithMeta = {
        ...state,
        _metadata: {
          version: '1.0.0',
          timestamp: new Date().toISOString(),
          lockId,
          pid: process.pid,
          nodeVersion: process.version
        }
      };
      
      // Create backup of current state if it exists
      await this._createStateBackup();
      
      // Write state atomically
      await atomicWriteFile(
        this.stateFile,
        JSON.stringify(stateWithMeta, null, 2),
        'utf8'
      );
      
      this._log('State saved successfully');
      
    } catch (error) {
      this._logError('Failed to save state:', error);
      throw new Error(`State save failed: ${error.message}`);
    }
  }

  /**
   * Load current state
   * @param {string} lockId - Lock ID for verification (optional)
   * @returns {Promise<Object>} - Current state
   */
  async loadState(lockId = null) {
    if (lockId) {
      this._verifyLock(lockId);
    }
    
    try {
      this._log('Loading current state...');
      
      // Check if state file exists
      try {
        await access(this.stateFile, constants.F_OK);
      } catch {
        this._log('No existing state file found, returning default state');
        return this._getDefaultState();
      }
      
      // Read state atomically
      const stateData = await atomicReadFile(this.stateFile, 'utf8');
      const state = JSON.parse(stateData);
      
      this._log('State loaded successfully');
      return state;
      
    } catch (error) {
      this._logError('Failed to load state:', error);
      throw new Error(`State load failed: ${error.message}`);
    }
  }

  /**
   * Create a backup of the current state
   * @private
   */
  async _createStateBackup() {
    try {
      // Check if current state exists
      try {
        await access(this.stateFile, constants.F_OK);
      } catch {
        this._log('No existing state to backup');
        return;
      }
      
      // Ensure backup directory exists
      await this._ensureDirectory(this.backupDir);
      
      // Create timestamped backup
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const backupFile = join(this.backupDir, `state-backup-${timestamp}.json`);
      
      const currentState = await readFile(this.stateFile, 'utf8');
      await atomicWriteFile(backupFile, currentState, 'utf8');
      
      this._log(`State backup created: ${backupFile}`);
      
      // Cleanup old backups (keep last 10)
      await this._cleanupOldBackups();
      
    } catch (error) {
      this._logError('Failed to create state backup:', error);
      // Don't throw - backup failure shouldn't stop the update
    }
  }

  /**
   * Restore state from backup
   * @param {string} backupFile - Backup file path (optional, uses latest if not provided)
   * @param {string} lockId - Lock ID for verification
   */
  async restoreFromBackup(backupFile = null, lockId) {
    this._verifyLock(lockId);
    
    try {
      this._log('Restoring state from backup...');
      
      let backupPath;
      if (backupFile) {
        backupPath = backupFile;
      } else {
        // Find latest backup
        backupPath = await this._getLatestBackup();
      }
      
      if (!backupPath) {
        throw new Error('No backup files found');
      }
      
      // Read backup and restore
      const backupData = await readFile(backupPath, 'utf8');
      await atomicWriteFile(this.stateFile, backupData, 'utf8');
      
      this._log(`State restored from: ${backupPath}`);
      
    } catch (error) {
      this._logError('Failed to restore from backup:', error);
      throw new Error(`State restore failed: ${error.message}`);
    }
  }

  /**
   * Get update progress information
   * @returns {Promise<Object>} - Progress information
   */
  async getProgress() {
    try {
      const state = await this.loadState();
      return {
        isUpdateInProgress: !!this.currentLock,
        currentPhase: state.currentPhase || 'idle',
        progress: state.progress || 0,
        startTime: state.startTime,
        lastUpdate: state._metadata?.timestamp,
        lockInfo: this.currentLock ? {
          id: this.currentLock.id,
          acquiredAt: this.currentLock.acquiredAt,
          pid: this.currentLock.pid
        } : null
      };
    } catch (error) {
      return {
        isUpdateInProgress: false,
        error: error.message
      };
    }
  }

  /**
   * Cleanup resources and release lock if held
   */
  async cleanup() {
    if (this.currentLock) {
      try {
        await this.releaseLock(this.currentLock.id);
      } catch (error) {
        this._logError('Error during cleanup:', error);
      }
    }
  }

  /**
   * Verify lock ownership
   * @private
   */
  _verifyLock(lockId) {
    if (!this.currentLock) {
      throw new Error('No active lock held');
    }
    
    if (this.currentLock.id !== lockId) {
      throw new Error(`Lock verification failed. Expected: ${this.currentLock.id}, Got: ${lockId}`);
    }
  }

  /**
   * Generate unique lock ID
   * @private
   */
  _generateLockId() {
    return `lock-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get default state structure
   * @private
   */
  _getDefaultState() {
    return {
      version: '1.0.0',
      currentPhase: 'idle',
      progress: 0,
      lastSuccessfulUpdate: null,
      rollbackInfo: null,
      imageVersions: {},
      schemaVersion: null
    };
  }

  /**
   * Ensure directory exists
   * @private
   */
  async _ensureDirectory(dirPath) {
    try {
      await mkdir(dirPath, { recursive: true });
    } catch (error) {
      if (error.code !== 'EEXIST') {
        throw error;
      }
    }
  }

  /**
   * Get latest backup file
   * @private
   */
  async _getLatestBackup() {
    try {
      const { readdir } = await import('node:fs/promises');
      const files = await readdir(this.backupDir);
      const backupFiles = files
        .filter(file => file.startsWith('state-backup-') && file.endsWith('.json'))
        .sort()
        .reverse();
      
      return backupFiles.length > 0 ? join(this.backupDir, backupFiles[0]) : null;
    } catch {
      return null;
    }
  }

  /**
   * Cleanup old backup files
   * @private
   */
  async _cleanupOldBackups() {
    try {
      const { readdir, unlink } = await import('node:fs/promises');
      const files = await readdir(this.backupDir);
      const backupFiles = files
        .filter(file => file.startsWith('state-backup-') && file.endsWith('.json'))
        .sort()
        .reverse();
      
      // Keep only the 10 most recent backups
      const filesToDelete = backupFiles.slice(10);
      for (const file of filesToDelete) {
        await unlink(join(this.backupDir, file));
        this._log(`Deleted old backup: ${file}`);
      }
    } catch (error) {
      this._logError('Failed to cleanup old backups:', error);
    }
  }

  /**
   * Logging utility
   * @private
   */
  _log(message) {
    if (this.verbose) {
      console.log(chalk.cyan('[StateManager]'), message);
    }
  }

  /**
   * Error logging utility
   * @private
   */
  _logError(message, error) {
    if (this.verbose) {
      console.error(chalk.red('[StateManager]'), message, error);
    }
  }
}

export default UpdateStateManager; 