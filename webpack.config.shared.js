const path = require("path");
const webpack = require("webpack");
const glob = require('glob');

module.exports = {
  config: {
    entry: {
      'root':  ['babel-polyfill',  './static/js/entry/root'],
      'error':  ['babel-polyfill',  './static/js/entry/error'],
      'style': "./static/js/entry/style"
    },
    module: {
      rules: [
        {
          test: /\.(png|svg|ttf|woff|woff2|eot|gif)$/,
          use: 'url-loader'
        },
      ]
    },
    resolve: {
      modules: [
        path.join(__dirname, "static/js"),
        "node_modules"
      ],
      extensions: ['.js', '.jsx'],
      alias: {
        'videojs-contrib-hls': path.resolve(__dirname, 'node_modules/videojs-contrib-hls/dist/videojs-contrib-hls.js'),
        'videojs-contrib-quality-levels': path.resolve(__dirname, 'node_modules/videojs-contrib-quality-levels/dist/videojs-contrib-quality-levels.js'),
      },
      mainFields: ['browser', 'module', 'main']
    },
    performance: {
      hints: false
    }
  },
  babelSharedLoader: {
    test: /\.jsx?$/,
    exclude: /node_modules/,
    loader: 'babel-loader',
    options: {
      "presets": [
        ["@babel/preset-env", { "modules": false }],
        "@babel/preset-react",
      ],
      "ignore": [
        "node_modules/**"
      ],
      "plugins": [
        "@babel/plugin-transform-flow-strip-types",
        "react-hot-loader/babel",
        "@babel/plugin-proposal-object-rest-spread",
        "@babel/plugin-proposal-class-properties",
        "@babel/plugin-syntax-dynamic-import",
      ]
    }
  },
};
