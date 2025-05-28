module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests', '<rootDir>/shared'],
  testMatch: [
    '**/__tests__/**/*.ts',
    '**/?(*.)+(spec|test).ts'
  ],
  collectCoverageFrom: [
    'shared/**/*.ts',
    '!shared/**/*.d.ts',
    '!shared/**/*.test.ts',
    '!shared/**/*.spec.ts'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: [
    'text',
    'lcov',
    'html'
  ],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  testTimeout: 10000,
  verbose: true,
  collectCoverage: false,
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/coverage/'
  ],
  moduleNameMapper: {
    '^axios$': '<rootDir>/tests/__mocks__/axios.ts'
  },
  clearMocks: true,
  restoreMocks: true
}; 