package com.ideaworks3d.thesims3;

/** Process-local ownership of the legacy JNI initialization, never saved state. */
final class RuntimeBootstrap {
    interface Initializer { void initialize() throws Throwable; }

    private Boolean graphicsCompatibility;
    private boolean initializing;
    private Throwable failure;

    synchronized boolean isReady() { return graphicsCompatibility != null; }

    synchronized void ensure(boolean graphics, Initializer initializer) throws Throwable {
        if (graphicsCompatibility != null) {
            if (graphicsCompatibility.booleanValue() != graphics)
                throw new IllegalStateException(
                        "Fully close the game before changing rendering mode, then retry.");
            return;
        }
        if (failure != null) throw failure;
        if (initializing) throw new IllegalStateException("Native startup is already in progress.");
        initializing = true;
        try {
            initializer.initialize();
            graphicsCompatibility = graphics;
        } catch (Throwable error) {
            // A partially initialized native image is not safe to retry in place.
            failure = error;
            throw error;
        } finally {
            initializing = false;
        }
    }
}
