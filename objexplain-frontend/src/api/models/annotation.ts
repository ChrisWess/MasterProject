import {User} from "./user";
import {Concept} from "./concept";

export type Annotation = {
    /**
     * ID of the Annotation
     */
    _id: string;
    /**
     * The original, unprocessed annotation text
     */
    text: string;
    /**
     * The tokenized annotation texts
     */
    tokens: string[];
    /**
     * The mask that shows where in the token list the concepts are located at
     */
    conceptMask: number[];
    /**
     * The list of IDs of all concepts that are present in the annotation text
     */
    conceptIds: string[];
    /**
     * The list of all concepts that are present in the annotation text
     */
    concepts: Concept[] | undefined;
    /**
     * The ID of the user that annotated the object
     */
    createdBy: string;
    /**
     * The user that annotated the object (i.e. the annotator)
     */
    createdByUser: User | undefined;
    /**
     * The timestamp of the creation of this Annotation with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    createdAt: string;
    /**
     * The timestamp of the last update of this Annotation with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    updatedAt: string;
}
