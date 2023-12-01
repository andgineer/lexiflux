const path = require('path');

module.exports = {
  setupFilesAfterEnv: [path.resolve(__dirname, 'tests/js/jest.setup.js')],
  testEnvironment: 'jsdom',
  testEnvironmentOptions: {
    html: '<html lang="zh-cmn-Hant"></html>',
  },
  roots: [
    "tests/js/"
  ],
};
