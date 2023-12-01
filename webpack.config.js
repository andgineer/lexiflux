const path = require('path');

module.exports = {
  entry: './lexiflux/static/lexiflux/main.js',
  output: {
    path: path.resolve(__dirname, 'lexiflux/static/lexiflux'),
    filename: 'bundle.js'
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader'
        }
      }
    ]
  },
  mode: 'development'  // 'production' // 'development' for non-minified output
};
