# Home page for chat.fosdem.org

A script to generate the home pages for [chat.fosdem.org](https://chat.fosdem.org/#/home) on Saturday and Sunday.

## Usage
### Generated files
The files are in `scripts/out` (one for Saturday, one for Sunday).

### Dependencies
_See requirements.txt_, in short:
 * Python 3
 * Jinja2

### Generating the files

Execute `scripts/home_from_penta.py`. The generated files will be in
`scripts/out`.

#### A note on `banner.svg`

Remember to strip out all leading elements from the file, such as `<?xml...>` so that the file begins with
`<svg>`. It makes browsers happy.

## License
[MIT license](LICENSE).