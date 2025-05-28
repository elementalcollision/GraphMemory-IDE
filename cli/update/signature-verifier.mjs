import { execSync, spawn } from 'node:child_process';
import { promisify } from 'node:util';
import chalk from 'chalk';

const execAsync = promisify(execSync);

/**
 * SignatureVerifier - Enterprise-grade Docker image signature verification
 * Implements Cosign (Sigstore) verification with support for:
 * - Keyless verification (OIDC + Fulcio CA + Rekor transparency log)
 * - Key-based verification (public/private keys or KMS)
 * - Trusted signer validation
 * - Comprehensive error handling and logging
 */
export class SignatureVerifier {
  constructor(options = {}) {
    this.cosignPath = options.cosignPath || 'cosign';
    this.trustedSigners = options.trustedSigners || [];
    this.keylessMode = options.keylessMode !== false; // Default to keyless
    this.publicKeyPath = options.publicKeyPath;
    this.timeout = options.timeout || 30000; // 30 second timeout
    this.verbose = options.verbose || false;
  }

  /**
   * Verify Docker image signature using Cosign
   * @param {string} imageRef - Full image reference (registry/repo:tag)
   * @param {Object} options - Verification options
   * @returns {Promise<{verified: boolean, details: Object}>}
   */
  async verifyImageSignature(imageRef, options = {}) {
    try {
      this._log(`Verifying signature for image: ${imageRef}`);
      
      // Check if cosign is available
      await this._checkCosignAvailable();
      
      // Prepare verification command
      const verifyCmd = this._buildVerifyCommand(imageRef, options);
      
      // Execute verification with timeout
      const result = await this._executeWithTimeout(verifyCmd, this.timeout);
      
      // Parse and validate result
      const verificationResult = this._parseVerificationResult(result, imageRef);
      
      this._log(`Verification result: ${verificationResult.verified ? 'PASSED' : 'FAILED'}`);
      
      return verificationResult;
      
    } catch (error) {
      this._logError(`Signature verification failed for ${imageRef}:`, error);
      return {
        verified: false,
        error: error.message,
        imageRef,
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Verify multiple images in parallel with concurrency control
   * @param {string[]} imageRefs - Array of image references
   * @param {Object} options - Verification options
   * @returns {Promise<Object>} - Results for all images
   */
  async verifyMultipleImages(imageRefs, options = {}) {
    const concurrency = options.concurrency || 3;
    const results = {};
    
    this._log(`Verifying ${imageRefs.length} images with concurrency ${concurrency}`);
    
    // Process images in batches
    for (let i = 0; i < imageRefs.length; i += concurrency) {
      const batch = imageRefs.slice(i, i + concurrency);
      const batchPromises = batch.map(imageRef => 
        this.verifyImageSignature(imageRef, options)
          .then(result => ({ imageRef, result }))
          .catch(error => ({ imageRef, result: { verified: false, error: error.message } }))
      );
      
      const batchResults = await Promise.all(batchPromises);
      batchResults.forEach(({ imageRef, result }) => {
        results[imageRef] = result;
      });
    }
    
    return results;
  }

  /**
   * Check if Cosign is available and properly configured
   * @private
   */
  async _checkCosignAvailable() {
    try {
      await execAsync(`${this.cosignPath} version`, { encoding: 'utf-8' });
    } catch (error) {
      throw new Error(`Cosign not found or not executable. Please install Cosign: ${error.message}`);
    }
  }

  /**
   * Build the cosign verify command based on configuration
   * @private
   */
  _buildVerifyCommand(imageRef, options) {
    let cmd = [this.cosignPath, 'verify'];
    
    if (this.keylessMode) {
      // Keyless verification using OIDC
      cmd.push('--certificate-identity-regexp', options.identityRegexp || '.*');
      cmd.push('--certificate-oidc-issuer-regexp', options.oidcIssuerRegexp || '.*');
    } else if (this.publicKeyPath) {
      // Key-based verification
      cmd.push('--key', this.publicKeyPath);
    } else {
      throw new Error('Either keyless mode must be enabled or public key path must be provided');
    }
    
    // Add trusted signers if specified
    if (this.trustedSigners.length > 0) {
      this.trustedSigners.forEach(signer => {
        cmd.push('--certificate-identity', signer);
      });
    }
    
    // Output format
    cmd.push('--output', 'json');
    
    // Add image reference
    cmd.push(imageRef);
    
    return cmd;
  }

  /**
   * Execute command with timeout
   * @private
   */
  async _executeWithTimeout(cmd, timeout) {
    return new Promise((resolve, reject) => {
      const process = spawn(cmd[0], cmd.slice(1), {
        stdio: ['pipe', 'pipe', 'pipe']
      });
      
      let stdout = '';
      let stderr = '';
      
      process.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      process.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      const timeoutId = setTimeout(() => {
        process.kill('SIGKILL');
        reject(new Error(`Verification timeout after ${timeout}ms`));
      }, timeout);
      
      process.on('close', (code) => {
        clearTimeout(timeoutId);
        
        if (code === 0) {
          resolve({ stdout, stderr, code });
        } else {
          reject(new Error(`Verification failed with code ${code}: ${stderr}`));
        }
      });
      
      process.on('error', (error) => {
        clearTimeout(timeoutId);
        reject(error);
      });
    });
  }

  /**
   * Parse cosign verification result
   * @private
   */
  _parseVerificationResult(result, imageRef) {
    try {
      const output = JSON.parse(result.stdout);
      
      return {
        verified: true,
        imageRef,
        signatures: output,
        timestamp: new Date().toISOString(),
        details: {
          signatureCount: Array.isArray(output) ? output.length : 1,
          verificationMethod: this.keylessMode ? 'keyless' : 'key-based'
        }
      };
    } catch (parseError) {
      // If JSON parsing fails, check if verification was successful
      if (result.code === 0) {
        return {
          verified: true,
          imageRef,
          timestamp: new Date().toISOString(),
          details: {
            verificationMethod: this.keylessMode ? 'keyless' : 'key-based',
            rawOutput: result.stdout
          }
        };
      }
      
      throw new Error(`Failed to parse verification result: ${parseError.message}`);
    }
  }

  /**
   * Logging utility
   * @private
   */
  _log(message) {
    if (this.verbose) {
      console.log(chalk.blue('[SignatureVerifier]'), message);
    }
  }

  /**
   * Error logging utility
   * @private
   */
  _logError(message, error) {
    if (this.verbose) {
      console.error(chalk.red('[SignatureVerifier]'), message, error);
    }
  }

  /**
   * Get verification status for display
   * @param {Object} result - Verification result
   * @returns {string} - Formatted status
   */
  static getStatusDisplay(result) {
    if (result.verified) {
      return chalk.green('✓ VERIFIED');
    } else {
      return chalk.red('✗ FAILED');
    }
  }
}

export default SignatureVerifier; 