export let debugLogging = true;

export function log(...args: any[]): void {
    if (debugLogging) {
        console.log(...args);
    }
}

export function getElement(id: string): HTMLElement {
    const result = document.getElementById(id);
    if (!result) {
        throw new Error(`Could not find element (id=${id}).`);
    }
    return result as HTMLElement;
}
