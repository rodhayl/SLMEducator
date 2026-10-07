export type WorkerUpdateResult = 'unsupported' | 'none' | 'requested' | 'failed';
type RegistrationReader = Pick<ServiceWorkerContainer, 'getRegistrations'>;
/** Ask only the known existing root worker to update. Normal browser activation owns retirement. */
export async function requestLegacyWorkerUpdate(
  serviceWorkers: RegistrationReader | undefined = navigator.serviceWorker,
  origin: string = window.location.origin,
): Promise<WorkerUpdateResult> {
  if (!serviceWorkers || typeof serviceWorkers.getRegistrations !== 'function') return 'unsupported';
  try {
    const registrations = await serviceWorkers.getRegistrations();
    const root = new URL('/', origin).href;
    const script = new URL('/sw.js', origin).href;
    const owned = registrations.filter(registration => {
      if (registration.scope !== root) return false;
      const workers = [registration.active, registration.waiting, registration.installing].filter(worker => worker !== null);
      return workers.length > 0 && workers.every(worker => worker.scriptURL === script);
    });
    if (!owned.length) return 'none';
    await Promise.all(owned.map(registration => registration.update()));
    // Updating is only a request. Never claim activation/unregistration or reload dirty pages.
    return 'requested';
  } catch { return 'failed'; }
}
