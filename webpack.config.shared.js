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
      extensions: ['.js', '.jsx', '.ts', '.tsx'],
      alias: {
        'videojs-contrib-hls': path.resolve(__dirname, 'node_modules/videojs-contrib-hls/dist/videojs-contrib-hls.js'),
        'videojs-contrib-quality-levels': path.resolve(__dirname, 'node_modules/videojs-contrib-quality-levels/dist/videojs-contrib-quality-levels.js'),
      }
    },
    performance: {
      hints: false
    }
  },
  babelSharedLoader: {
    test: /\.[jt]sx?$/,
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
        "@babel/plugin-proposal-object-rest-spread",
        "@babel/plugin-proposal-class-properties",
        "@babel/plugin-syntax-dynamic-import",
      ],
      // Flow and TypeScript syntax cannot both be enabled on one file, so the
      // type-stripping transform is selected by extension. .js/.jsx keep Flow
      // while the migration is in progress; .ts/.tsx get TypeScript. When the
      // last Flow annotation is gone, the first override and
      // @babel/plugin-transform-flow-strip-types go with it.
      "overrides": [
        {
          "test": /\.jsx?$/,
          "plugins": ["@babel/plugin-transform-flow-strip-types"]
        },
        {
          "test": /\.tsx?$/,
          "presets": ["@babel/preset-typescript"]
        }
      ]
    }
  },
};
