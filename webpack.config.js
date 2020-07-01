var path = require('path');
var webpack = require('webpack');
var pkg = require('./package.json');
var HtmlWebpackPlugin = require('html-webpack-plugin');
var CleanWebpackPlugin = require('clean-webpack-plugin');
var CopyPlugin = require('copy-webpack-plugin');

var PATHS = {
    dist: path.join(__dirname, './frontend/dist/'),
    src: path.join(__dirname, './frontend/src/')
  };

module.exports = {
    entry: './frontEnd/src/app.js',
    output: {
        filename: '[name].[contenthash].js',
        path: PATHS.dist
    },
    optimization: {
		splitChunks: {
			cacheGroups: {
				commons: {
					test: /[\\/]node_modules[\\/]/,
					name: 'vendors',
					chunks: 'all'
				}
			}
		}
	},
    module: {
        rules: [
            { test: /\.css$/, use: ['style-loader', 'css-loader' ] },
            { test: /\.png$/, loader: 'url-loader?limit=8192', query: { mimetype: 'image/png' } },
            { test: /\.woff($|\?)|\.woff2($|\?)|\.ttf($|\?)|\.eot($|\?)|\.svg($|\?)/, loader: 'url-loader' },
            { test: /\.js?$/, exclude: '/node_modules/', use: { loader: 'babel-loader' } },
            { test: /\.html$/, loader: 'raw-loader' }
        ]
    },
    plugins: [
        new webpack.ProvidePlugin({
            '$': 'jquery',
            'Util': 'exports-loader?Util!bootstrap/js/dist/util'
        }),
        new webpack.DefinePlugin( {'VERSION': JSON.stringify(pkg.version) }),
        new HtmlWebpackPlugin({
            filename: 'index.html',
            inject: 'head',
            template: './frontEnd/src/index.html'
        }),
        new CleanWebpackPlugin(),
        new CopyPlugin([
            { from: './frontEnd/src/*.json', to: './', flatten: true },
            { from: './frontEnd/src/images', to: './images' },
            { from: './frontEnd/src/*.php', to: './', flatten: true },
			{ from: './backEnd/*.py', to: './' },
			{ from: './docs/_build/', to: './docs/',}
          ]),
        new webpack.ContextReplacementPlugin(
            /moment[/\\]locale$/,
            /en/
        )
    ],
    devServer: {
        open: true,
        port: 8008
    }
};
