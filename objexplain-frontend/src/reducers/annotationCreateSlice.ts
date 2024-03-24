import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {Annotation} from "../api/models/annotation";
import {Concept} from "../api/models/concept";

interface NewAnnotationPageState {
    modeId: number;
    newAnnotation: Annotation | undefined;
    conceptRanges: [number, number][] | undefined;
    adjectives: string[][];
    nouns: string[][];
    adjectiveIdxs: number[][];
    nounIdxs: number[][];
    conceptEditIdx: number;
}

const initialState: NewAnnotationPageState = {
    modeId: 0,
    newAnnotation: undefined,
    conceptRanges: undefined,
    adjectives: [],
    nouns: [],
    adjectiveIdxs: [],
    nounIdxs: [],
    conceptEditIdx: 0,
};

export const newAnnotationPageSlice = createSlice({
    name: "newAnno",
    initialState,
    reducers: {
        setMode: (state, action: PayloadAction<number>) => {
            state.modeId = action.payload;
        },
        clearNewAnnoView: (state) => {
            state.modeId = 0;
        },
        addNewConceptDraft: (state) => {
            let adjArr = state.adjectives;
            let nounArr = state.nouns;
            let aidxs = state.adjectiveIdxs;
            let nidxs = state.nounIdxs;
            adjArr.push([])
            nounArr.push([])
            aidxs.push([])
            nidxs.push([])
            state.adjectives = adjArr;
            state.nouns = nounArr;
            state.adjectiveIdxs = aidxs;
            state.nounIdxs = nidxs;
            state.conceptEditIdx = state.conceptEditIdx + 1;
        },
        addAdjective: (state, action: PayloadAction<[string, number]>) => {
            let adjective = action.payload[0];
            let idx = action.payload[1];
            let adjArr = state.adjectives
            let aidxs = state.adjectiveIdxs;
            adjArr[state.conceptEditIdx].push(adjective)
            state.adjectives = adjArr
            aidxs[state.conceptEditIdx].push(idx);
            state.adjectiveIdxs = aidxs;
        },
        addNoun: (state, action: PayloadAction<[string, number]>) => {
            let noun = action.payload[0];
            let idx = action.payload[1];
            let nounArr = state.nouns
            let nidxs = state.nounIdxs;
            nounArr[state.conceptEditIdx].push(noun)
            state.nouns = nounArr
            nidxs[state.conceptEditIdx].push(idx);
            state.nounIdxs = nidxs;
        },
        setConceptEditIdx: (state, action: PayloadAction<number>) => {
            state.conceptEditIdx = action.payload;
        },
        addFullConcept: (state, action: PayloadAction<Concept>) => {
            let concept = action.payload;
            let adjs = state.adjectives;
            let nouns = state.nouns;
            let conceptTokens = concept.phraseWords
            let nounsStart = concept.nounCount - conceptTokens.length
            adjs.push(conceptTokens.slice(0, nounsStart))
            nouns.push(conceptTokens.slice(nounsStart + 1))
            state.adjectives = adjs;
            state.nouns = nouns;
            let aidxs = state.adjectiveIdxs;
            let nidxs = state.nounIdxs;
            aidxs.push(concept.phraseIdxs.slice(0, nounsStart))
            nidxs.push(concept.phraseIdxs.slice(nounsStart + 1))
            state.adjectiveIdxs = aidxs;
            state.nounIdxs = nidxs;
        },
    }
});

// actions
export const {
    setMode, clearNewAnnoView, addNewConceptDraft, addAdjective,
    addNoun, setConceptEditIdx, addFullConcept,
} = newAnnotationPageSlice.actions;

export default newAnnotationPageSlice.reducer;