import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {Annotation} from "../api/models/annotation";
import {Concept} from "../api/models/concept";

interface NewAnnotationPageState {
    modeId: number;
    suggestedText: string | undefined;
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
    suggestedText: undefined,
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
        clearNewAnnoView: (state) => {
            state.modeId = 0;
            state.suggestedText = undefined
            state.newAnnotation = undefined
            state.conceptRanges = undefined
            state.adjectives = []
            state.nouns = []
            state.adjectiveIdxs = []
            state.nounIdxs = []
            state.conceptEditIdx = 0
        },
        clearSuggestedText: (state) => {
            state.suggestedText = undefined
        },
        clearConcepts: (state) => {
            state.adjectives = []
            state.nouns = []
            state.adjectiveIdxs = []
            state.nounIdxs = []
            state.conceptEditIdx = 0
        },
        setMode: (state, action: PayloadAction<number>) => {
            state.modeId = action.payload;
        },
        setSuggestedText: (state, action: PayloadAction<string>) => {
            state.suggestedText = action.payload;
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
        },
        addAdjective: (state, action: PayloadAction<[string, number]>) => {
            let adjective = action.payload[0];
            let idx = action.payload[1];
            let adjArr = state.adjectives;
            let aidxs = state.adjectiveIdxs;
            let editIdx = state.conceptEditIdx;
            if (!editIdx && adjArr.length === 0) {
                let nounArr = state.nouns;
                let nidxs = state.nounIdxs;
                adjArr.push([adjective])
                aidxs.push([idx])
                nounArr.push([])
                nidxs.push([])
                state.nouns = nounArr;
                state.nounIdxs = nidxs;
            } else {
                adjArr[editIdx].push(adjective)
                aidxs[editIdx].push(idx);
            }
            state.adjectives = adjArr
            state.adjectiveIdxs = aidxs;
        },
        addNoun: (state, action: PayloadAction<[string, number]>) => {
            let noun = action.payload[0];
            let idx = action.payload[1];
            let nounArr = state.nouns
            let nidxs = state.nounIdxs;
            let editIdx = state.conceptEditIdx;
            if (!editIdx && nounArr.length === 0) {
                let adjArr = state.adjectives;
                let aidxs = state.adjectiveIdxs;
                adjArr.push([])
                aidxs.push([])
                nounArr.push([noun])
                nidxs.push([idx])
                state.adjectives = adjArr;
                state.adjectiveIdxs = aidxs;
            } else {
                nounArr[editIdx].push(noun)
                nidxs[editIdx].push(idx);
            }
            state.nouns = nounArr;
            state.nounIdxs = nidxs;
        },
        resetDraft: (state) => {
            // TODO
        },
        setConceptEditIdx: (state, action: PayloadAction<number>) => {
            state.conceptEditIdx = action.payload;
        },
        addFullConcept: (state, action: PayloadAction<Concept>) => {
            let concept = action.payload;
            let adjs = state.adjectives;
            let nouns = state.nouns;
            let conceptTokens = concept.phraseWords
            let nounsStart = conceptTokens.length - concept.nounCount
            adjs.push(conceptTokens.slice(0, nounsStart))
            nouns.push(conceptTokens.slice(nounsStart))
            state.adjectives = adjs;
            state.nouns = nouns;
            let aidxs = state.adjectiveIdxs;
            let nidxs = state.nounIdxs;
            aidxs.push(concept.phraseIdxs.slice(0, nounsStart))
            nidxs.push(concept.phraseIdxs.slice(nounsStart))
            state.adjectiveIdxs = aidxs;
            state.nounIdxs = nidxs;
        },
        addFullConcepts: (state, action: PayloadAction<Concept[]>) => {
            let concepts = action.payload;
            let adjs = state.adjectives;
            let nouns = state.nouns;
            let aidxs = state.adjectiveIdxs;
            let nidxs = state.nounIdxs;
            concepts.map(concept => {
                let conceptTokens = concept.phraseWords
                let nounsStart = conceptTokens.length - concept.nounCount
                adjs.push(conceptTokens.slice(0, nounsStart))
                nouns.push(conceptTokens.slice(nounsStart))
                aidxs.push(concept.phraseIdxs.slice(0, nounsStart))
                nidxs.push(concept.phraseIdxs.slice(nounsStart))
            })
            state.adjectives = adjs;
            state.nouns = nouns;
            state.adjectiveIdxs = aidxs;
            state.nounIdxs = nidxs;
        },
    }
});

// actions
export const {
    setMode, setSuggestedText, clearNewAnnoView, clearConcepts,
    clearSuggestedText, addNewConceptDraft, addAdjective, addNoun,
    setConceptEditIdx, addFullConcept, addFullConcepts,
} = newAnnotationPageSlice.actions;

export default newAnnotationPageSlice.reducer;