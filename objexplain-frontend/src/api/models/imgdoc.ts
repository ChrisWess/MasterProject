import {DetectedObject} from "./object";
import {User} from "./user";

export type ImageDocument = {
    /**
     * ID of the Image Document
     */
    _id: string;
    /**
     * Name of the Image Document
     */
    name: string;
    /**
     * File name of the Image file
     */
    fname: string;
    /**
     * The base64 string data of the image file
     */
    image: string | undefined;
    /**
     * The base64 string data of the thumbnail image
     */
    thumbnail: string | undefined;
    /**
     * The pixel width of the image
     */
    width: number;
    /**
     * The pixel height of the image
     */
    height: number;
    /**
     * The list of IDs of all detected objects that were identified in the image
     */
    objIds: string[];
    /**
     * The list of all detected objects that were identified in the image
     */
    objects: DetectedObject[] | undefined;
    /**
     * The ID of the user who uploaded the image
     */
    createdBy: string;
    /**
     * The user who uploaded the image
     */
    createdByUser: User | undefined;
    /**
     * The timestamp of the creation of this Image Document with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    createdAt: string;
    /**
     * The timestamp of the last update of this Image Document with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    updatedAt: string;
}
