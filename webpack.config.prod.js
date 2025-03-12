var webpack = require('webpack');
var path = require("path");
var BundleTracker = require('webpack-bundle-tracker');
const glob = require('glob');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const { config, babelSharedLoader } = require(path.resolve("./webpack.config.shared.js"));

const prodBabelConfig = Object.assign({}, babelSharedLoader);

prodBabelConfig.query.plugins.push(
  "transform-react-constant-elements",
  "transform-react-inline-elements"
);

const prodConfig = Object.assign({}, config);
prodConfig.module.rules = [
  prodBabelConfig,
  ...config.module.rules,
  {
    test: /\.css$|\.scss$/,
    use:  [
      {
        loader: MiniCssExtractPlugin.loader
      },
      "css-loader",
      "postcss-loader",
      {
        loader: 'sass-loader',
        options: {
          sassOptions: {
            sourceMap: true,
            includePaths: ['node_modules', 'node_modules/@material/*']
              .map(dir => path.join(__dirname, dir))
              .map(fullPath => glob.sync(fullPath))
              .reduce((acc, matches) => acc.concat(matches), [])
          }
        }
      }
    ]
  }
];

module.exports = Object.assign(prodConfig, {
  context: __dirname,
  mode:    "production",
  output: {
    path: path.resolve('./static/bundles/'),
    filename: "[name]-[chunkhash].js",
    chunkFilename: "[id]-[chunkhash].js",
    crossOriginLoading: "anonymous",
  },

  plugins: [
    new webpack.DefinePlugin({
      'process.env': {
        'NODE_ENV': '"production"'
      }
    }),
    // This is necessary to make videojs & uglify work together:
    // https://github.com/videojs/videojs-contrib-hls/issues/600#issuecomment-295730581
    new webpack.DefinePlugin({
      'typeof global': JSON.stringify('undefined')
    }),
    new BundleTracker({
      filename: 'webpack-stats.json'
    }),
    new webpack.LoaderOptionsPlugin({
      minimize: true
    }),
    new webpack.optimize.AggressiveMergingPlugin(),
    new MiniCssExtractPlugin({
      filename: "[name]-[contenthash].css",
      allChunks: true,
      ignoreOrder: false,
    })
  ],
  optimization: {
    splitChunks: {
      name:      "common",
      minChunks: 2
    },
    minimize: true
  },
  devtool: 'source-map'
});
