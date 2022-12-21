//const PYODIDE_PATH = "pyodide"; // this is the one installed with npm install
const PYODIDE_PATH = "..//0.21.3/pyodide";
//const PYODIDE_PATH = "../0.22.0.dev0/zipimport2/pyodide";

const { loadPyodide } = require(PYODIDE_PATH);

async function main() {
    console.log(PYODIDE_PATH);
    console.time('loadPyodide');
    let pyodide = await loadPyodide();
    console.timeEnd('loadPyodide');

    try {
        console.time('runPython');
        pyodide.runPython(`
            print('hello world');
        `);
        console.timeEnd('runPython');
    }
    catch(e) {
        console.log(e.message);
    }
}

main();
