export type CorpusWord = {
    /**
     * ID of the Concept
     */
    _id: string;
    /**
     * The corpus index value that is unique regarding the group of all words with the same lemma
     */
    index: number;
    /**
     * The lower-case string of this word without formatting (only hyphenation allowed)
     */
    text: string;
    /**
     * The lower-case string of the word's lemma
     */
    lemma: string;
    /**
     * The lower-case string of the word stem
     */
    stem: string | undefined;
    /**
     * A flag denoting, if this word is a noun or not (if not, it should be an adjective)
     */
    nounFlag: boolean;
}
