export type Label = {
    /**
     * ID of the Label
     */
    _id: string;
    /**
     * Name that is used to describe the label
     */
    name: string;
    /**
     * Tokenized list of the name (into list of word-string)
     */
    nameTokens: string[];
    /**
     * Index of the label
     */
    labelIdx: number;
    /**
     * Word indices of the label tokens
     */
    tokenRefs: number[];
    /**
     * Categories of the label
     */
    categories: string[];
}
