var webpack = require('webpack');
var path = require("path");
var R = require('ramda');
var BundleTracker = require('webpack-bundle-tracker');
const glob = require('glob');
const { config, babelSharedLoader } = require(path.resolve("./webpack.config.shared.js"));

const hotEntry = (host, port) => (
  `webpack-hot-middleware/client?path=http://${host}:${port}/__webpack_hmr&timeout=20000&reload=true`
);

const insertHotReload = (host, port, entries) => (
  R.map(R.compose(R.flatten, v => [v].concat(hotEntry(host, port))), entries)
);

const devConfig = Object.assign({}, config, {
  context: __dirname,
  mode:    "development",
  output: {
    path: path.resolve('./static/bundles/'),
    filename: "[name].js"
  },
  plugins: [
    new webpack.DefinePlugin({
      "process.env": {
        NODE_ENV: '"development"'
      }
    }),
    new webpack.HotModuleReplacementPlugin(),
    new BundleTracker({ path: __dirname, filename: "webpack-stats.json" })
  ],
  devtool: 'source-map',
  optimization: {
    moduleIds: 'named',
    splitChunks:  {
      chunks: 'all',
    },
    emitOnErrors: false,
  }
});

devConfig.module.rules = [
  babelSharedLoader,
  ...config.module.rules,
  {
    test: /\.css$|\.scss$/,
    use: [
      {loader: 'style-loader'},
      {loader: 'css-loader', options: {esModule: false}},
      {loader: 'postcss-loader', options: {sourceMap: true}},
      {
        loader: 'sass-loader',
        options: {
          implementation: require('sass'),
          sassOptions: {
            sourceMap: true,
            includePaths: ['node_modules', 'node_modules/@material/*']
              .map(dir => path.join(__dirname, dir))
              .map(fullPath => glob.sync(fullPath))
              .reduce((acc, matches) => acc.concat(matches), [])
          }
        }
      },
    ]
  },
];

const makeDevConfig = (host, port) => (
  Object.assign({}, devConfig, {
    entry: insertHotReload(host, port, devConfig.entry),
  })
);

module.exports = makeDevConfig;
