const path = require('path');

module.exports = {
  entry: './lexiflux/viewport/main.ts',
  output: {
    path: path.resolve(__dirname, 'lexiflux/static/lexiflux'),
    filename: 'bundle.js'
  },
  resolve: {
    extensions: ['.ts', '.js'], // Add .ts
  },
  module: {
    rules: [
      {
        test: /\.ts$/, // Changed to .ts
        exclude: /node_modules/,
        use: {
          loader: 'ts-loader' // Changed to ts-loader
        }
      }
    ]
  },
  mode: 'production' // 'development' for non-minified output
};
