# Home page for chat.fosdem.org

A script to generate the home pages for [chat.fosdem.org](https://chat.fosdem.org/#/home) on Saturday and Sunday.

## Usage
### Generated files
The files are in `scripts/out` (one for Saturday, one for Sunday).

### Dependencies
_See requirements.txt_, in short:
 * Python 3
 * Jinja2
 * Pyyaml

### Generating the files
To generate them yourself, follow the instructions on [the FOSDEM website](https://github.com/FOSDEM/website#exporting-from-fosdem-pentabarf)
to generate a local export of the Pentabarf database (only available
to FOSDEM staff), or use the provided (mostly current for 2022) `pentabarf.yaml` file.
If you use your own local export, copy it to `scripts/pentabarf.yaml`.

Execute `scripts/home_from_penta.py`. The generated files will be in
`scripts/out`.

#### A note on `banner.svg`

Remember to strip out all leading elements from the file, such as `<?xml...>` so that the file begins with
`<svg>`. It makes browsers happy.

## License
[MIT license](LICENSE).