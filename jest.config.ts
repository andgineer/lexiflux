import path from 'path';

export default {
  setupFilesAfterEnv: [
      path.resolve(__dirname, 'tests/js/jest.setup.ts'),
  ],
  testEnvironment: 'allure-jest/jsdom',
  testEnvironmentOptions: {
    html: '<html lang="zh-cmn-Hant"></html>',
    resultsDir: "./allure-results",
  },
  roots: [
    "tests/js/"
  ],
  transform: {
    "^.+\\.tsx?$": ['ts-jest', {
      tsconfig: 'tsconfig.json',
    }],
  },
  // Coverage configuration here
  collectCoverage: true,
  coverageDirectory: "coverage",
  coverageReporters: ["text", "lcov", "html"],
  collectCoverageFrom: [
    "lexiflux/viewport/**/*.ts",
    "!**/node_modules/**",
    "!**/*.d.ts"
  ],
};
