import {Annotation} from "./annotation";
import {User} from "./user";
import {Label} from "./label";

export type DetectedObject = {
    /**
     * ID of the Annotation
     */
    _id: string;
    /**
     * The ID of the class label that this object depicts
     */
    labelId: string;
    /**
     * The class label that this object depicts
     */
    label: Label | undefined;
    /**
     * Top left x-coordinate of the bounding box
     */
    tlx: number;
    /**
     * Top left y-coordinate of the bounding box
     */
    tly: number;
    /**
     * Bottom right x-coordinate of the bounding box
     */
    brx: number;
    /**
     * Bottom right y-coordinate of the bounding box
     */
    bry: number;
    /**
     * The list of annotations that were written for this object
     */
    annotations: Annotation[] | undefined;
    /**
     * The ID of the user that selected the object (created the bbox)
     */
    createdBy: string;
    /**
     * The user that selected the object
     */
    createdByUser: User | undefined;
    /**
     * The timestamp of the creation of this object with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    createdAt: string;
    /**
     * The timestamp of the last update of this object with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    updatedAt: string;
}
