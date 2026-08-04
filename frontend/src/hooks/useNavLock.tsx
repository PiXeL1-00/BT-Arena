"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface NavLockContextValue {
    locked: boolean;
    lock: () => void;
    unlock: () => void;
}

const NavLockContext = createContext<NavLockContextValue>({
    locked: false,
    lock: () => { },
    unlock: () => { },
});

export function NavLockProvider({ children }: { children: ReactNode }) {
    const [locked, setLocked] = useState(false);
    const lock = useCallback(() => setLocked(true), []);
    const unlock = useCallback(() => setLocked(false), []);

    return (
        <NavLockContext.Provider value={{ locked, lock, unlock }}>
            {children}
        </NavLockContext.Provider>
    );
}

export function useNavLock() {
    return useContext(NavLockContext);
}
