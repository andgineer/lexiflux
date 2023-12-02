import path from 'path';

export default {
  setupFilesAfterEnv: [path.resolve(__dirname, 'tests/js/jest.setup.ts')],
  testEnvironment: 'jsdom',
  testEnvironmentOptions: {
    html: '<html lang="zh-cmn-Hant"></html>',
  },
  roots: [
    "tests/js/"
  ],
  transform: {
    "^.+\\.tsx?$": ['ts-jest', {
      tsconfig: 'tsconfig.json',
    }],
  },
};
