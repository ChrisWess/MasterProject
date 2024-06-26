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
    selectedConceptIdx: number | undefined;
    conceptsSelected: boolean[];
    suggestedConcepts: Concept[];
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
    selectedConceptIdx: undefined,
    conceptsSelected: [],
    suggestedConcepts: [],
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
            state.conceptsSelected = []
            state.suggestedConcepts = []
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
            if (adjArr.length === 0) {
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
            if (nounArr.length === 0) {
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
        switchAdj: (state, action: PayloadAction<[number, number]>) => {
            let fromIdx = action.payload[0];
            let toIdx = action.payload[1];
            let adjArr = state.adjectives;
            let aidxs = state.adjectiveIdxs;
            let editIdx = state.conceptEditIdx;
            let currAdjs = adjArr[editIdx]
            let currIdxs = aidxs[editIdx]
            let fromVal = currAdjs[fromIdx]
            let fromValIdx = currIdxs[fromIdx]
            let toVal = currAdjs[toIdx]
            let toValIdx = currIdxs[toIdx]
            currAdjs[toIdx] = fromVal
            currAdjs[fromIdx] = toVal
            currIdxs[toIdx] = fromValIdx
            currIdxs[fromIdx] = toValIdx
            state.adjectives[editIdx] = currAdjs
            state.adjectiveIdxs[editIdx] = currIdxs;
        },
        switchNoun: (state, action: PayloadAction<[number, number]>) => {
            let fromIdx = action.payload[0];
            let toIdx = action.payload[1];
            let nounArr = state.nouns;
            let nidxs = state.nounIdxs;
            let editIdx = state.conceptEditIdx;
            let currNouns = nounArr[editIdx]
            let currIdxs = nidxs[editIdx]
            let fromVal = currNouns[fromIdx]
            let fromValIdx = currIdxs[fromIdx]
            let toVal = currNouns[toIdx]
            let toValIdx = currIdxs[toIdx]
            currNouns[toIdx] = fromVal
            currNouns[fromIdx] = toVal
            currIdxs[toIdx] = fromValIdx
            currIdxs[fromIdx] = toValIdx
            state.nouns[editIdx] = currNouns
            state.nounIdxs[editIdx] = currIdxs;
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
        removeSelectedConcept: (state, action: PayloadAction<number>) => {
            let rmvAt = action.payload
            let adjs = state.adjectives;
            let nouns = state.nouns;
            let aidxs = state.adjectiveIdxs;
            let nidxs = state.nounIdxs;
            adjs.splice(rmvAt, 1)
            nouns.splice(rmvAt, 1)
            aidxs.splice(rmvAt, 1)
            nidxs.splice(rmvAt, 1)
            state.adjectives = adjs;
            state.nouns = nouns;
            state.adjectiveIdxs = aidxs;
            state.nounIdxs = nidxs;
            let idx = state.conceptEditIdx;
            if (idx !== 0 && idx >= rmvAt) {
                state.conceptEditIdx = idx - 1;
            }
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
        pushSuggestedConcepts: (state, action: PayloadAction<Concept[]>) => {
            let oldConcepts = state.suggestedConcepts
            let selections = state.conceptsSelected
            let concepts = action.payload;
            oldConcepts.push(...concepts);
            selections.push(...Array(concepts.length).fill(false));
            state.suggestedConcepts = oldConcepts
            state.conceptsSelected = selections
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
    addSelectedConcept, removeSelectedConcept, selectConceptIdx, setSuggestedConcepts,
    pushSuggestedConcepts, setSuggestedAdjectives, setSuggestedNouns, setNewAnnotation,
    switchAdj, switchNoun,
} = newAnnotationPageSlice.actions;

export default newAnnotationPageSlice.reducer;