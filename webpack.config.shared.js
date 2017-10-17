const path = require("path");
const webpack = require("webpack");
const glob = require('glob');

module.exports = {
  config: {
    entry: {
      'collections': ['babel-polyfill', './static/js/entry/collections'],
      'error': ['babel-polyfill', './static/js/entry/error'],
      'video_detail': ['babel-polyfill', './static/js/entry/video_detail'],
      'video_embed': ['babel-polyfill', './static/js/entry/video_embed'],
      'style': './static/js/entry/style',
    },
    module: {
      rules: [
        {
          test: /\.(png|svg|ttf|woff|woff2|eot|gif)$/,
          use: 'url-loader'
        },
        {
          test: /\.scss$/,
          use: [
            {
              loader: 'style-loader',
              options: {
                sourceMap: true
              }
            },
            {
              loader: 'css-loader',
              options: {
                sourceMap: true
              }
            },
            {
              loader: 'postcss-loader',
              options: {
                sourceMap: true
              }
            },
            {
              loader: 'sass-loader',
              options: {
                sourceMap: true,
                includePaths: ['node_modules', 'node_modules/@material/*']
                  .map(dir => path.join(__dirname, dir))
                  .map(fullPath => glob.sync(fullPath))
                  .reduce((acc, matches) => acc.concat(matches), []),
              }
            },
          ]
        },
        {
          test: /\.css$/,
          exclude: /node_modules/,
          use: [
            { loader: 'style-loader' },
            { loader: 'css-loader' }
          ]
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
      }
    },
    performance: {
      hints: false
    }
  },
  babelSharedLoader: {
    test: /\.jsx?$/,
    exclude: /node_modules/,
    loader: 'babel-loader',
    query: {
      "presets": [
        ["env", { "modules": false }],
        "latest",
        "react",
      ],
      "ignore": [
        "node_modules/**"
      ],
      "plugins": [
        "transform-flow-strip-types",
        "react-hot-loader/babel",
        "transform-object-rest-spread",
        "transform-class-properties",
        "syntax-dynamic-import",
      ]
    }
  },
};
