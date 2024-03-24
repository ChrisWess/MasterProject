import {CorpusWord} from "./corpus";

export type Concept = {
    /**
     * ID of the Concept
     */
    _id: string;
    /**
     * The unique key string of the Concept
     */
    key: string;
    /**
     * The list of phrase word indices in the corpus (used to define the key)
     */
    phraseIdxs: number[];
    /**
     * The Corpus ID of the Concept's defining noun
     */
    rootNoun: string;
    /**
     * The list of IDs in the corpus of all phrase words of this Concept
     */
    phraseWordIds: string[];
    /**
     * The list of data of all phrase words in the corpus of this Concept
     */
    phraseWordsData: CorpusWord[] | undefined;
    /**
     * The list of all phrase words (just the word-strings) of this Concept
     */
    phraseWords: string[];
    /**
     * Number that shows how many nouns are part of this concept's phrase (the trailing words)
     */
    nounCount: number;
    /**
     * The index of the model's conv-filter, which is looking for this Concept
     */
    convFilterIdx: number;
    /**
     * The timestamp of the last update of this Concept with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    updatedAt: string;
    /**
     * The timestamp of the creation of this Concept with date format YYYY-MM-DD"T"HH:MM:SS.
     */
    createdAt: string;
}
