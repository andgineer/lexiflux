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

export function showModal(modalId: string): void {
    const modal = document.getElementById(modalId);
    if (modal instanceof HTMLElement) {
        modal.classList.add('show');
        modal.style.display = 'block';
        modal.removeAttribute('aria-hidden');
        const firstInput = modal.querySelector('input');
        if (firstInput instanceof HTMLInputElement) {
            firstInput.focus();
        }
    }
}

export function closeModal(modalId: string): void {
    const modal = document.getElementById(modalId);
    if (modal instanceof HTMLElement) {
        modal.classList.remove('show');
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    }
}