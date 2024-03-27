import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {Annotation} from "../api/models/annotation";
import {Concept} from "../api/models/concept";
import {CorpusWord} from "../api/models/corpus";

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
    annosSelected: boolean[] | undefined;
    conceptsSelected: boolean[] | undefined;
    selectedConceptIdx: number | undefined;
    suggestedConcepts: Concept[] | undefined;
    suggestedAdjectives: CorpusWord[] | undefined;
    suggestedNouns: CorpusWord[] | undefined;
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
    annosSelected: undefined,
    conceptsSelected: undefined,
    selectedConceptIdx: undefined,
    suggestedConcepts: undefined,
    suggestedAdjectives: undefined,
    suggestedNouns: undefined,
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
            state.selectedConceptIdx = undefined
            state.annosSelected = undefined
            state.conceptsSelected = undefined
            state.suggestedConcepts = undefined
            state.suggestedAdjectives = undefined
            state.suggestedNouns = undefined
        },
        clearSuggestedText: (state) => {
            state.suggestedText = undefined
            state.annosSelected = undefined
        },
        clearConcepts: (state) => {
            state.adjectives = []
            state.nouns = []
            state.adjectiveIdxs = []
            state.nounIdxs = []
            state.conceptEditIdx = 0
            state.selectedConceptIdx = undefined
            let concepts = state.suggestedConcepts
            if (concepts) {
                state.conceptsSelected = Array(concepts.length).fill(false)
            }
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
            state.conceptEditIdx = adjArr.length - 1
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
        removeAdjectiveAt: (state, action: PayloadAction<number>) => {
            let rmvIdx = action.payload;
            let editIdx = state.conceptEditIdx;
            let adjArr = state.adjectives;
            let aidxs = state.adjectiveIdxs;
            adjArr[editIdx].splice(rmvIdx, 1)
            aidxs[editIdx].splice(rmvIdx, 1)
            state.adjectives = adjArr;
            state.adjectiveIdxs = aidxs;
        },
        removeNounAt: (state, action: PayloadAction<number>) => {
            let rmvIdx = action.payload;
            let editIdx = state.conceptEditIdx;
            let nounArr = state.nouns;
            let nidxs = state.nounIdxs;
            nounArr[editIdx].splice(rmvIdx, 1)
            nidxs[editIdx].splice(rmvIdx, 1)
            state.nouns = nounArr;
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
        initAnnoSelectionFlags: (state, action: PayloadAction<number>) => {
            state.annosSelected = Array(action.payload).fill(false);
        },
        markAnnoSelected: (state, action: PayloadAction<number>) => {
            let flags = state.annosSelected;
            if (flags) {
                flags[action.payload] = true;
                state.annosSelected = flags;
            }
        },
        initConceptSelectionFlags: (state, action: PayloadAction<number>) => {
            state.conceptsSelected = Array(action.payload).fill(false);
        },
        selectConceptIdx: (state, action: PayloadAction<number>) => {
            state.selectedConceptIdx = action.payload;
        },
        addSelectedConcept: (state) => {
            let idx = state.selectedConceptIdx;
            let flags = state.conceptsSelected;
            let concepts = state.suggestedConcepts;
            if (idx !== undefined && concepts && flags) {
                let concept = concepts[idx];
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
                flags[idx] = true;
                state.conceptsSelected = flags;
                state.selectedConceptIdx = undefined
            }
        },
        setSuggestedConcepts: (state, action: PayloadAction<Concept[]>) => {
            let concepts = action.payload;
            state.suggestedConcepts = concepts;
            state.conceptsSelected = Array(concepts.length).fill(false);

        },
        setSuggestedAdjectives: (state, action: PayloadAction<CorpusWord[]>) => {
            state.suggestedAdjectives = action.payload;
        },
        setSuggestedNouns: (state, action: PayloadAction<CorpusWord[]>) => {
            state.suggestedNouns = action.payload;
        },
        setNewAnnotation: (state, action: PayloadAction<Annotation>) => {
            let anno = action.payload;
            let ranges: [number, number][] = []
            let prevVal = -1
            for (let i = 0; i < anno.conceptMask.length; i++) {
                let maskVal = anno.conceptMask[i];
                if (maskVal === -1) {
                    if (prevVal !== maskVal) {
                        ranges[ranges.length - 1][1] = i - 1
                        if (ranges.length === anno.conceptIds.length) {
                            break
                        }
                    }
                } else if (prevVal === -1) {
                    ranges.push([i, -1])
                } else if (prevVal !== maskVal) {
                    ranges[ranges.length - 1][1] = i - 1
                    ranges.push([i, -1])
                }
                prevVal = maskVal;
            }
            state.newAnnotation = anno;
            state.conceptRanges = ranges;
        },
    }
});

// actions
export const {
    setMode, setSuggestedText, clearNewAnnoView, clearConcepts,
    clearSuggestedText, addNewConceptDraft, addAdjective, addNoun,
    removeAdjectiveAt, removeNounAt, setConceptEditIdx, addFullConcept,
    addFullConcepts, initAnnoSelectionFlags, markAnnoSelected, initConceptSelectionFlags,
    addSelectedConcept, selectConceptIdx, setSuggestedConcepts, setSuggestedAdjectives,
    setSuggestedNouns, setNewAnnotation,

} = newAnnotationPageSlice.actions;

export default newAnnotationPageSlice.reducer;