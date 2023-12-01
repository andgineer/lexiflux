module.exports = {
    log,
    suppressRedraw,
    resumeRedraw
};

let debugLogging = true;
function log(...args) {
    if (debugLogging) {
        console.log(...args);
    }
}

let redrawSuppressCount = 0;

function suppressRedraw(container) {
    if (redrawSuppressCount === 0) {
        container.style.visibility = 'hidden';
    }
    redrawSuppressCount++;
}

function resumeRedraw(container) {
    redrawSuppressCount--;
    if (redrawSuppressCount === 0) {
        container.style.visibility = 'visible';
    } else if (redrawSuppressCount < 0) {
        console.error('Mismatched calls to suppressRedraw and resumeRedraw');
        redrawSuppressCount = 0; // Reset to prevent further errors
    }
}
