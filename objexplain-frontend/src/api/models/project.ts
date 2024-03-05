export type Project = {
    /**
     * ID of the Project
     */
    _id: string;
    /**
     * The Project's title
     */
    title: string;
    /**
     * The Project description
     */
    description: string | undefined;
    /**
     * Tags that describe the cause of the Project
     */
    tags: string[];
}


export type ProjectStats = {
    /**
     * ID of the Project
     */
    _id: string;
    /**
     * The Project's title
     */
    title: string;
    /**
     * The Project description
     */
    description: string | undefined;
    /**
     * Tags that describe the cause of the Project
     */
    tags: string[];
    /**
     * The number of Image Documents uploaded to this Project
     */
    numDocs: number;
    /**
     * The decimal [0,1] representing the completion progress of the project (1.0 means 100% annotation coverage)
     */
    progress: number;
}
