export enum UserRole {
    ADMIN = 0,
    MANAGER = 1,
    ANNOTATOR = 2,
}

export type User = {
    /**
     * ID of the User
     */
    _id: string;
    /**
     * E-Mail of the User
     */
    email: string;
    /**
     * Username
     */
    name: string | undefined;
    /**
     * Role of the User
     */
    role: UserRole;
    /**
     * Color of the User Avatar
     */
    color: string;
    /**
     * Flag if the user account is active
     */
    active: boolean;
}
