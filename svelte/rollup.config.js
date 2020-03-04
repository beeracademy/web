import svelte from 'rollup-plugin-svelte';
import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import livereload from 'rollup-plugin-livereload';
import { terser } from 'rollup-plugin-terser';
import babel from 'rollup-plugin-babel';
import fs from 'fs';

const production = !process.env.ROLLUP_WATCH;

const outputDir = 'static/svelte';

const exports = [];
fs.readdirSync('src').map(fname => {
	if (!fname.endsWith('.js')) return;

	const base = fname.substr(0, fname.length - 3);

	if (!fs.existsSync(`src/${base}.svelte`)) return;

	exports.push({
		input: `src/${base}.js`,
		output: {
			sourcemap: true,
			format: 'iife',
			name: 'app',
			file: `${outputDir}/${base}.js`
		},
		plugins: [
			svelte({
				// enable run-time checks when not in production
				dev: !production,
				// we'll extract any component CSS out into
				// a separate file — better for performance
				css: css => {
					css.write(`${outputDir}/${base}.css`);
				}
			}),

			babel({
				extensions: ['.js', '.mjs', '.html', '.svelte'],
				include: ['src/**', 'node_modules/svelte/**'],
				presets: [
					["@babel/env", {
						useBuiltIns: 'usage',
						corejs: 3,
					}],
				],
			}),

			// If you have external dependencies installed from
			// npm, you'll most likely need these plugins. In
			// some cases you'll need additional configuration —
			// consult the documentation for details:
			// https://github.com/rollup/plugins/tree/master/packages/commonjs
			resolve({
				browser: true,
				dedupe: importee => importee === 'svelte' || importee.startsWith('svelte/')
			}),
			commonjs(),

			// In dev mode, call `npm run start` once
			// the bundle has been generated
			!production && serve(),

			// Watch the `public` directory and refresh the
			// browser on changes when not in production
			!production && livereload('public'),

			// If we're building for production (npm run build
			// instead of npm run dev), minify
			production && terser()
		],
		watch: {
			clearScreen: false,
			chokidar: false,
		}
	});
});

export default exports;

function serve() {
	let started = false;

	return {
		writeBundle() {
			if (!started) {
				started = true;

				require('child_process').spawn('npm', ['run', 'start', '--', '--dev'], {
					stdio: ['ignore', 'inherit', 'inherit'],
					shell: true
				});
			}
		}
	};
}
