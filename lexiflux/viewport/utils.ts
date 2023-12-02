export let debugLogging = true;

export function log(...args: any[]): void {
    if (debugLogging) {
        console.log(...args);
    }
}

let redrawSuppressCount = 0;

export function suppressRedraw(container: HTMLElement): void {
    if (redrawSuppressCount === 0) {
        container.style.visibility = 'hidden';
    }
    redrawSuppressCount++;
}

export function resumeRedraw(container: HTMLElement): void {
    redrawSuppressCount--;
    if (redrawSuppressCount === 0) {
        container.style.visibility = 'visible';
    } else if (redrawSuppressCount < 0) {
        console.error('Mismatched calls to suppressRedraw and resumeRedraw');
        redrawSuppressCount = 0; // Reset to prevent further errors
    }
}
