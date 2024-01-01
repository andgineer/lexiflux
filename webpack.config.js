const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');

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
  optimization: {
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          // mangle: false, // Disable name mangling
          mangle: {
            // List of function names to preserve from minification
            keep_fnames: ['goToPage'],
          },
        },
      }),
    ],
  },
  mode: 'production' // 'development' for non-minified output
};
