import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {VisualFeature} from "../api/models/feature";
import {Annotation} from "../api/models/annotation";

interface AnnotationPageState {
    annotationIdx: number | undefined;
    annotation: Annotation | undefined;
    selectedConcept: number | undefined;
    markedWords: number[];
    wordFlags: boolean[] | undefined;
    markedWordsPrevColors: string[] | undefined;
    conceptSubstrings: string[] | undefined;
    conceptRanges: [number, number][] | undefined;
    objImgUrl: string | undefined;
    showFeatures: boolean;
    featuresVis: boolean[];
    features: (VisualFeature | string)[];
    showConcepts: boolean;
    showHoverText: boolean;
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
    objImgUrl: undefined,
    showFeatures: true,
    featuresVis: [],
    features: [],
    showConcepts: true,
    showHoverText: true,
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
        addConceptAt: (state, action: PayloadAction<number>) => {
            let addedIdx = action.payload
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
        setObjImgUrl: (state, action: PayloadAction<string>) => {
            state.objImgUrl = action.payload;
        },
        clearAnnotationView: (state) => {
            state.featuresVis = [];
            state.features = [];
            state.annotation = undefined;
            state.conceptSubstrings = undefined;
            state.objImgUrl = undefined;
        },
        switchFeaturesVisible: (state) => {
            state.showFeatures = !state.showFeatures;
        },
        switchFeatVisible: (state, action: PayloadAction<number>) => {
            let payload = action.payload;
            if (state.featuresVis && payload >= 0 && payload < state.featuresVis.length) {
                let prev = state.featuresVis;
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
        toggleHoverText: (state) => {
            state.showHoverText = !state.showHoverText;
        },
    }
});

// actions
export const {
    setAnnotationIdx, setAnnotation, setSelectedConcept, clearSelectedConcept,
    setWordFlags, setMarkedWords, setPrevColors, clearPrevColors,
    setConceptSubs, setConceptRanges, setObjImgUrl, switchFeaturesVisible,
    switchFeatVisible, setFeatures, removeConceptAt, addConceptAt,
    extractConceptInfo, toggleHoverText,
} = annotationPageSlice.actions;

export default annotationPageSlice.reducer;