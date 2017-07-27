var webpack = require('webpack');
var path = require("path");
var BundleTracker = require('webpack-bundle-tracker');
const { config, babelSharedLoader } = require(path.resolve("./webpack.config.shared.js"));

const prodBabelConfig = Object.assign({}, babelSharedLoader);

prodBabelConfig.query.plugins.push(
  "transform-react-constant-elements",
  "transform-react-inline-elements"
);

const prodConfig = Object.assign({}, config);
prodConfig.module.rules = [prodBabelConfig, ...config.module.rules];

module.exports = Object.assign(prodConfig, {
  context: __dirname,
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
    new webpack.optimize.UglifyJsPlugin({
      compress: {
        warnings: false
      },
      sourceMap: true,
    }),
    new webpack.optimize.CommonsChunkPlugin({
      name: 'common',
      minChunks: 2,
    }),
    new BundleTracker({
      filename: './webpack-stats.json'
    }),
    new webpack.LoaderOptionsPlugin({
      minimize: true
    }),
    new webpack.optimize.AggressiveMergingPlugin(),
  ],
  devtool: 'source-map'
});
