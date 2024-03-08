import {User} from "./user";

export type BoundingBox = {
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
}

export type VisualFeature = {
    /**
     * ID of the Visual Feature
     */
    _id: string;
    /**
     * The ID of the object
     */
    objectId: string;
    /**
     * The ID of the annotation
     */
    annotationId: string;
    /**
     * The ID of the concept
     */
    conceptId: string;
    /**
     * The bounding boxes that mark the concept's area in the object
     */
    bboxs: BoundingBox[] | undefined;
    /**
     * The ID of the user that selected the feature
     */
    createdBy: string;
    /**
     * The user that selected the feature
     */
    createdByUser: User | undefined;
    /**
     * The timestamp of the creation of this feature with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    createdAt: string;
    /**
     * The timestamp of the last update of this feature with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    updatedAt: string;
}
