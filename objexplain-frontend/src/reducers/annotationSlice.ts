import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {VisualFeature} from "../api/models/feature";
import {Annotation} from "../api/models/annotation";
import {Concept} from "../api/models/concept";

interface AnnotationPageState {
    annotationIdx: number | undefined;
    annotation: Annotation | undefined;
    selectedConcept: number | undefined;
    markedWords: number[];
    wordFlags: boolean[] | undefined;
    markedWordsPrevColors: string[] | undefined;
    conceptSubstrings: string[] | undefined;
    conceptRanges: [number, number][] | undefined;
    showFeatures: boolean;
    featuresVis: boolean[];
    features: (VisualFeature | string)[];
    conceptInfo: Concept | undefined;
    showConcepts: boolean;
    showHoverText: boolean;
    isConceptExpanded: boolean;
}

const initialState: AnnotationPageState = {
    annotationIdx: undefined,
    annotation: undefined,
    selectedConcept: undefined,
    markedWords: [],
    wordFlags: undefined,
    markedWordsPrevColors: undefined,
    conceptSubstrings: undefined,
    conceptRanges: undefined,
    showFeatures: true,
    featuresVis: [],
    features: [],
    conceptInfo: undefined,
    showConcepts: true,
    showHoverText: true,
    isConceptExpanded: false,
};

export const annotationPageSlice = createSlice({
    name: "annotation",
    initialState,
    reducers: {
        setAnnotationIdx: (state, action: PayloadAction<number>) => {
            state.annotationIdx = action.payload;
        },
        setAnnotation: (state, action: PayloadAction<Annotation>) => {
            state.annotation = action.payload;
        },
        setSelectedConcept: (state, action: PayloadAction<number>) => {
            state.selectedConcept = action.payload;
        },
        clearSelectedConcept: (state) => {
            state.selectedConcept = undefined;
        },
        removeConceptAt: (state, action: PayloadAction<number>) => {
            state.selectedConcept = undefined;
            let rmvIdx = action.payload
            let ranges = state.conceptRanges;
            if (ranges) {
                ranges.splice(rmvIdx, 1)
                state.conceptRanges = ranges
            }
            let strings = state.conceptSubstrings;
            if (strings) {
                strings.splice(rmvIdx, 1)
                state.conceptSubstrings = strings
            }
            let visArr = state.featuresVis;
            if (visArr) {
                visArr.splice(rmvIdx, 1)
                state.featuresVis = visArr
            }
            let featsArr = state.features;
            if (featsArr) {
                featsArr.splice(rmvIdx, 1)
                state.features = featsArr
            }
        },
        addConceptAt: (state, action: PayloadAction<[number, string]>) => {
            let addedIdx = action.payload[0]
            state.selectedConcept = addedIdx;
            let marked = state.markedWords;
            if (marked.length === 1) {
                let val = marked[0]
                marked = [val, val + 1]
            }
            if (marked.length === 2) {
                let startIdx = marked[0]
                let endIdx = marked[1]
                let ranges = state.conceptRanges;
                if (ranges) {
                    // @ts-ignore
                    ranges.splice(addedIdx, 0, [startIdx, endIdx - 1])
                    state.conceptRanges = ranges
                }
                let strings = state.conceptSubstrings;
                if (strings && state.annotation) {
                    let tokens = state.annotation.tokens
                    let newString = ''
                    for (let i = startIdx; i < endIdx; i++) {
                        let token = tokens[i];
                        if (!newString || token === ',' || token === '.') {
                            newString += token
                        } else {
                            newString += ' ' + token
                        }
                    }
                    strings.splice(addedIdx, 0, newString);
                    state.conceptSubstrings = strings;
                }
                let features = state.features;
                if (features) {
                    features.splice(addedIdx, 0, action.payload[1])
                    state.features = features
                }
                let visArr = state.featuresVis;
                if (visArr) {
                    visArr.splice(addedIdx, 0, true)
                    state.featuresVis = visArr
                }
            }
        },
        extractConceptInfo: (state, action: PayloadAction<Annotation>) => {
            let anno = action.payload
            let conceptStrings: string[] = []
            let ranges: [number, number][] = []
            let prevVal = -1
            let currString = ''
            for (let i = 0; i < anno.tokens.length; i++) {
                let maskVal = anno.conceptMask[i];
                if (maskVal >= 0) {
                    if (prevVal === -1 || prevVal === maskVal) {
                        if (!currString) {
                            ranges.push([i, -1])
                        }
                        let token = anno.tokens[i];
                        if (currString.length === 0 || token === ',' || token === '.') {
                            currString += token
                        } else {
                            currString += ' ' + token
                        }
                    } else {
                        conceptStrings.push(currString)
                        ranges[ranges.length - 1][1] = i - 1
                        currString = anno.tokens[i];
                    }
                } else if (currString.length > 0) {
                    conceptStrings.push(currString)
                    ranges[ranges.length - 1][1] = i - 1
                    currString = '';
                }
                prevVal = maskVal;
            }
            state.conceptSubstrings = conceptStrings
            state.conceptRanges = ranges
        },
        setWordFlags: (state, action: PayloadAction<boolean[]>) => {
            state.wordFlags = action.payload;
        },
        setMarkedWords: (state, action: PayloadAction<number[]>) => {
            state.markedWords = action.payload;
        },
        setPrevColors: (state, action: PayloadAction<string[]>) => {
            state.markedWordsPrevColors = action.payload;
        },
        clearPrevColors: (state) => {
            state.markedWordsPrevColors = undefined;
        },
        setConceptSubs: (state, action: PayloadAction<string[]>) => {
            state.conceptSubstrings = action.payload;
        },
        setConceptRanges: (state, action: PayloadAction<[number, number][]>) => {
            state.conceptRanges = action.payload;
        },
        clearAnnotationView: (state) => {
            state.annotationIdx = undefined;
            state.annotation = undefined;
            state.selectedConcept = undefined;
            state.markedWords = [];
            state.wordFlags = undefined;
            state.markedWordsPrevColors = undefined;
            state.conceptSubstrings = undefined;
            state.conceptRanges = undefined;
            state.showFeatures = true;
            state.featuresVis = [];
            state.features = [];
            state.conceptInfo = undefined;
            state.showConcepts = true;
            state.showHoverText = true;
            state.isConceptExpanded = false;
        },
        switchFeaturesVisible: (state) => {
            state.showFeatures = !state.showFeatures;
        },
        switchFeatVisible: (state, action: PayloadAction<number>) => {
            let payload = action.payload;
            let prev = state.featuresVis;
            if (prev && payload >= 0 && payload < prev.length) {
                prev[payload] = !prev[payload];
                state.featuresVis = prev;
            }
        },
        setFeatures: (state, action: PayloadAction<(VisualFeature | string)[]>) => {
            let features = action.payload;
            if (features.length > 0) {
                let featVis = []
                for (let i = 0; i < features.length; i++) {
                    featVis.push(!!features[i])
                }
                state.featuresVis = featVis;
            }
            state.features = features
        },
        setConceptInfo: (state, action: PayloadAction<Concept>) => {
            state.conceptInfo = action.payload;
        },
        toggleShowConcepts: (state) => {
            state.showConcepts = !state.showConcepts;
        },
        toggleHoverText: (state) => {
            state.showHoverText = !state.showHoverText;
        },
        toggleConceptExpanded: (state) => {
            state.isConceptExpanded = !state.isConceptExpanded;
        },
    }
});

// actions
export const {
    setAnnotationIdx, setAnnotation, setSelectedConcept, clearSelectedConcept,
    setWordFlags, setMarkedWords, setPrevColors, clearPrevColors,
    switchFeaturesVisible, switchFeatVisible, setConceptInfo, setFeatures,
    removeConceptAt, addConceptAt, extractConceptInfo,
    toggleShowConcepts, toggleHoverText, toggleConceptExpanded,
    clearAnnotationView,
} = annotationPageSlice.actions;

export default annotationPageSlice.reducer;