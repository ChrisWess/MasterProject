import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest} from "../api/requests";
import {FC, useEffect, useMemo, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setDoc, setImgUrl} from "../reducers/idocSlice";
import {setProject} from "../reducers/mainPageSlice";
import {Button, Typography} from "@mui/material";
import {ImageDocument} from "../api/models/imgdoc";
import {loadDocImage, loadProject} from "../document/ProjectIDocPage";
import {setObject, setObjectIdx, setObjectLabel} from "../reducers/objectSlice";
import {Annotation} from "../api/models/annotation";
import AnnotationControlPanel from "./AnnotationControl";
import {
    clearPrevColors,
    clearSelectedConcept,
    extractConceptInfo,
    setAnnotation,
    setAnnotationIdx,
    setFeatures,
    setMarkedWords,
    setPrevColors,
    setSelectedConcept,
    setWordFlags
} from "../reducers/annotationSlice";
import {VisualFeature} from "../api/models/feature";
import {cropImage, loadDoc} from "../object_annotator/ObjectPage";
import {setTitle} from "../reducers/appBarSlice";
import {Label} from "../api/models/label";
import {ReactJSXElement} from "@emotion/react/types/jsx-namespace";
import HoverBox, {Highlighted} from "./HoverBox";


export const CONCEPT_COLORS = [
    '#FDA172',
    '#808000',
    '#469990',
    '#B2560D',
    '#DCBEFF',
    '#404040',
    '#AAFFC3',
    '#F032E6',
    '#6495ED',
    '#228B22',
]


export const loadVisualFeatures = async (annoId: string) => {
    return await getRequest('visFeature/annotation', annoId)
}

const AnnotationView: FC = () => {
    const {projectName, docId, objIdx, annoIdx} = useParams();
    const context: any = useOutletContext();
    const imgContainer = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const imgUrl: string | undefined = useSelector((state: any) => state.iDoc.imgUrl);
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);
    const annotation: Annotation | undefined = useSelector((state: any) => state.annotation.annotation);
    const markedWords: number[] = useSelector((state: any) => state.annotation.markedWords);
    const wordFlags: boolean[] = useSelector((state: any) => state.annotation.wordFlags);
    const prevWordColors: string[] | undefined = useSelector((state: any) => state.annotation.markedWordsPrevColors);
    const featsVis: boolean[] = useSelector((state: any) => state.annotation.featuresVis);
    const showFeats: boolean = useSelector((state: any) => state.annotation.showFeatures);
    const features: (VisualFeature | string)[] = useSelector((state: any) => state.annotation.features);
    const conceptSubs: string[] | undefined = useSelector((state: any) => state.annotation.conceptSubstrings);
    const conceptRanges: [number, number][] | undefined = useSelector((state: any) => state.annotation.conceptRanges);
    const showConcepts: boolean = useSelector((state: any) => state.annotation.showConcepts);
    const hoverToggle: boolean = useSelector((state: any) => state.annotation.showHoverText);

    let objIntIdx = objIdx ? parseInt(objIdx) : undefined;
    let annoIntIdx = annoIdx ? parseInt(annoIdx) : undefined;

    /**
     * The concepts in the annotation are marked with the same color as the bounding boxes of the
     * visual features (of the object) to easily identify which feature displays which concept.
     */

    const generateFeatureBBoxs = () => {
        if (idoc && featsVis && conceptSubs && features && imgContainer.current) {
            let imgHeight = imgContainer.current.offsetHeight
            if (imgHeight > 0) {
                let ratio = imgHeight / idoc.height
                return conceptSubs.map((conceptString, index) => {
                    let feat = features[index]
                    if (typeof feat !== 'string' && featsVis[index]) {
                        let feature: VisualFeature = feat
                        let color = CONCEPT_COLORS[index % 10];
                        // Supply text only for first bbox (use the text part of the concept of current annotation)
                        return feature.bboxs!.map((bbox, idx) => {
                            let key = feature._id + '_' + idx;
                            if (idx === 0) {
                                return <Box key={key} position='absolute' border='solid 5px'
                                            borderColor={color}
                                            sx={{top: ratio * bbox.tlx - 5, left: ratio * bbox.tly - 5}}
                                            width={ratio * (bbox.brx - bbox.tlx) + 10}
                                            height={ratio * (bbox.bry - bbox.tly) + 10}
                                            onClick={() => {
                                                // TODO
                                            }}>
                                    <Typography color={color} sx={{fontSize: '14px', ml: '4px'}}>
                                        <b color={color}>{conceptString}</b>
                                    </Typography>
                                </Box>
                            } else {
                                return <Box key={key} position='absolute' border='solid 5px' borderColor={color}
                                            sx={{top: ratio * bbox.tlx - 5, left: ratio * bbox.tly - 5}}
                                            width={ratio * (bbox.brx - bbox.tlx) + 10}
                                            height={ratio * (bbox.bry - bbox.tly) + 10}
                                            onClick={() => {
                                                // TODO
                                            }}/>
                            }
                        })
                    }
                });
            }
        }
    }

    const bboxs = useMemo(generateFeatureBBoxs, [idoc, conceptSubs, features, featsVis])

    const clearPrevMarking = () => {
        if (prevWordColors) {
            if (markedWords.length === 1) {
                let prev = document.getElementById("w" + markedWords[0])
                if (prev) {  // && prev.classList.contains("wregular")
                    prev.style.backgroundColor = prevWordColors[0]
                }
            } else if (markedWords.length === 2) {
                let wordsStartIdx = markedWords[0]
                for (let i = wordsStartIdx; i < markedWords[1]; i++) {
                    let prev = document.getElementById("w" + i)
                    let prevColor = prevWordColors[i - wordsStartIdx]
                    if (prev) {  // && prev.classList.contains("wregular")
                        prev.style.backgroundColor = prevColor
                    }
                    if (i > wordsStartIdx) {
                        prev = document.getElementById("ws" + i)
                        if (prev) {
                            prev.style.backgroundColor = prevColor
                        }
                    }
                }
            }
        }
    };

    const setNewConceptSelection = (value: any) => {
        clearPrevMarking()
        if (!value) {
            dispatch(clearSelectedConcept())
        } else {
            let idx;
            if (typeof value === 'number') {
                idx = value;
            } else {
                idx = parseInt(value.currentTarget.id.substring(1));
            }
            let range = conceptRanges![idx]
            dispatch(setMarkedWords([range[0], range[1] + 1]))
            dispatch(setSelectedConcept(idx))
        }
        dispatch(clearPrevColors())
    }

    const getStyle = function (element: any, property: string) {
        return window.getComputedStyle ? window.getComputedStyle(element, null).getPropertyValue(property) :
            element.style[property.replace(/-([a-z])/g, function (g) {
                return g[1].toUpperCase();
            })];
    };

    const markWords = (markRange: number[]) => {
        clearPrevMarking();
        let prevColors = []
        if (markRange.length === 1) {
            let element = document.getElementById("w" + markRange[0])
            if (element) {
                prevColors.push(getStyle(element, "background-color"));
                element.style.backgroundColor = "deepskyblue";
                dispatch(setMarkedWords(markRange));
            } else {
                dispatch(setMarkedWords([]));
            }
        } else if (markRange.length === 2) {
            let startIdx = markRange[0];
            for (let i = startIdx; i < markRange[1]; i++) {
                let prev = document.getElementById("w" + i)
                if (prev) {
                    prevColors.push(getStyle(prev, "background-color"));
                    prev.style.backgroundColor = "deepskyblue"
                }
                if (i > startIdx) {
                    prev = document.getElementById("ws" + i)
                    if (prev) {
                        prev.style.backgroundColor = "deepskyblue"
                    }
                }
            }
            dispatch(setMarkedWords(markRange))
        } else {
            dispatch(setMarkedWords([]));
        }
        dispatch(setPrevColors(prevColors))
    }

    const highlightedAnnotation = useMemo(() => {
        let buffer: ReactJSXElement[] = new Array<ReactJSXElement>()
        if (annotation && conceptRanges) {
            let tokens: string[] = annotation.tokens;
            let flags: boolean[] = []
            let currRange = 0;
            let idxStart = -1;
            let idxEnd = -1;
            if (conceptRanges.length > currRange) {
                idxStart = conceptRanges[currRange][0];
                idxEnd = conceptRanges[currRange][1];
            }
            for (let i = 0; i < tokens.length; i++) {
                let token: string = tokens[i];
                let isPunct = token.match(/^[.,:!?;]$/);
                flags.push(!isPunct)
                if (!showConcepts || idxStart === -1 || idxStart > i) {
                    let currentId = 'w' + i;
                    if (isPunct) {
                        if (markedWords.length != 0 && i >= markedWords[0] && i < markedWords[1]) {
                            buffer.push(<abbr key={currentId} id={currentId}><Highlighted text={token}/></abbr>);
                        } else {
                            buffer.push(<abbr key={currentId} id={currentId}>{token}</abbr>);
                        }
                    } else {
                        if (markedWords.length != 0 && i >= markedWords[0] && i < markedWords[1]) {
                            if (i == markedWords[0]) {
                                buffer.push(<abbr id={'ws' + i} key={'wSpace' + i}>{' '}</abbr>)
                                buffer.push(<abbr key={currentId} id={currentId} className="wregular"><Highlighted
                                    text={token}/></abbr>);
                            } else {
                                buffer.push(<abbr id={'ws' + i} key={'wSpace' + i}><Highlighted text={' '}/></abbr>)
                                if (i == markedWords[1] - 1) {
                                    buffer.push(<abbr key={currentId} id={currentId} className="wregular"><Highlighted
                                        text={token}/></abbr>);
                                } else {
                                    buffer.push(<abbr key={currentId} id={currentId} className="wregular"
                                                      style={{backgroundColor: "deepskyblue"}}>{token}</abbr>);
                                }
                            }
                        } else {
                            buffer.push(<abbr id={'ws' + i} key={'wSpace' + i}>{' '}</abbr>)
                            buffer.push(<abbr key={currentId} id={currentId} className="wregular">{token}</abbr>)
                        }
                    }
                } else if (i === idxEnd) {
                    let id = 'w' + idxStart
                    let currentId = 'c' + currRange;
                    if (idxStart === idxEnd) {
                        buffer.push(<b key={currentId} id={currentId} onClick={setNewConceptSelection}>
                            {" "}
                            <abbr
                                key={id + "-1"}
                                id={id}
                                className={"cr cr-" + currRange}>
                                <a key={id + "-2"} id={id + '-open'} href="">[</a>
                                <HoverBox
                                    word={tokens[idxStart]}
                                    conceptIdx={currRange}
                                    hovertoggle={hoverToggle}
                                    annotation={annotation}
                                    color={CONCEPT_COLORS[currRange % 10]}/>
                                <a key={id + "-4"} id={id + '-close'} href="">]</a>
                                <sub key={id + "-5"} id={id + '-nr'}>{currRange + 1}</sub>
                            </abbr>
                        </b>)
                    } else {
                        let idEnd = "w" + idxEnd;
                        buffer.push(
                            <b key={currentId} id={currentId} onClick={setNewConceptSelection}>
                                {" "}
                                <abbr key={id + "-1"} id={id} className={"cr cr-" + currRange}
                                      style={{backgroundColor: CONCEPT_COLORS[currRange % 10]}}>
                                    <a key={id + "-2"} id={id + '-open'} href="">[</a>
                                    <HoverBox
                                        word={tokens[idxStart]}
                                        conceptIdx={currRange}
                                        hovertoggle={hoverToggle}
                                        annotation={annotation}
                                        color={CONCEPT_COLORS[currRange % 10]}/>
                                </abbr>
                                {tokens.slice(idxStart + 1, idxEnd).map((elem, index) => {
                                    let tokenIdx = idxStart + index + 1
                                    return <abbr key={'w' + tokenIdx + "-1"}
                                                 id={'w' + tokenIdx}
                                                 className={"cr cr-" + currRange}
                                                 style={{backgroundColor: CONCEPT_COLORS[currRange % 10]}}>
                                        {flags[tokenIdx] && " "}
                                        <HoverBox
                                            word={elem}
                                            conceptIdx={currRange}
                                            hovertoggle={hoverToggle}
                                            annotation={annotation}
                                            color={CONCEPT_COLORS[currRange % 10]}/>
                                    </abbr>
                                })}
                                <abbr key={idEnd + "-1"} id={idEnd} className={"cr cr-" + currRange}
                                      style={{backgroundColor: CONCEPT_COLORS[currRange % 10]}}>
                                    {" "}
                                    <HoverBox
                                        word={tokens[idxEnd]}
                                        conceptIdx={currRange}
                                        hovertoggle={hoverToggle}
                                        annotation={annotation}
                                        color={CONCEPT_COLORS[currRange % 10]}/>
                                    <a key={idEnd + "-2"} id={idEnd + '-close'} href="">]</a>
                                    <sub key={idEnd + "-3"} id={idEnd + '-nr'}>{currRange + 1}</sub>
                                </abbr>
                            </b>)
                    }
                } else {
                    continue;
                }
                if (showConcepts && i === idxEnd) {
                    ++currRange;
                    if (conceptRanges.length > currRange) {
                        idxStart = conceptRanges[currRange][0];
                        idxEnd = conceptRanges[currRange][1];
                    } else {
                        idxStart = -1;
                        idxEnd = -1;
                    }
                }
            }
            dispatch(setWordFlags(flags));
        }
        return buffer
    }, [annotation, conceptRanges, markedWords, hoverToggle, showConcepts])

    useEffect(() => {
        if (!projectName) {
            navigate('/notfound404')
        } else if (!project || project.title != projectName) {
            loadProject(projectName).then(projectData => projectData ?
                dispatch(setProject(projectData.result)) :
                navigate('/notfound404'))
        }
        if (!docId) {
            navigate('/notfound404')
        } else if (!idoc || idoc._id != docId) {
            loadDoc(docId).then(idocData => {
                if (idocData) {
                    dispatch(setDoc(idocData.result));
                    loadDocImage(docId).then(file => {
                        file && dispatch(setImgUrl(file))
                    });
                } else {
                    navigate('/notfound404')
                }
            })
        }
        context.setControlPanel(<AnnotationControlPanel/>)
    }, []);

    useEffect(() => {
        if (idoc && imgUrl) {
            if (idoc.objects && objIntIdx !== undefined && annoIntIdx !== undefined &&
                objIntIdx >= 0 && annoIntIdx >= 0 && objIntIdx < idoc.objects.length) {
                let annotations = idoc.objects[objIntIdx].annotations;
                if (annotations && annoIntIdx < annotations.length) {
                    dispatch(setObjectIdx(objIntIdx));
                    let obj = idoc.objects[objIntIdx];
                    dispatch(setObject(obj));
                    if (objectLabel) {
                        dispatch(setTitle(`Annotation ${annoIntIdx + 1} of Object ${objectLabel.name}`));
                    } else {
                        getRequest('label', obj.labelId).then(data => {
                            if (data) {
                                let label = data.result;
                                dispatch(setObjectLabel(label));
                                dispatch(setTitle(`Annotation ${annoIntIdx! + 1} of Object ${label.name}`));
                            }
                        })
                    }
                    let newWidth = obj.brx - obj.tlx
                    let newHeight = obj.bry - obj.tly
                    cropImage(canvasRef, imgUrl, obj.tlx, obj.tly, newWidth, newHeight)
                    dispatch(setAnnotationIdx(annoIntIdx));
                    let currAnno = annotations[annoIntIdx];
                    if (!annotation || currAnno._id !== annotation._id) {
                        dispatch(setAnnotation(currAnno));
                        dispatch(extractConceptInfo(currAnno));
                    }
                    loadVisualFeatures(currAnno._id).then(data => {
                        if (data) {
                            let featArr: (VisualFeature | string)[] = []
                            let features = data.result
                            if (currAnno.conceptIds.length > 0) {
                                for (let i = 0; i < currAnno.conceptIds.length; i++) {
                                    let cid = currAnno.conceptIds[i];
                                    for (let j = 0; j < features.length; j++) {
                                        let feat = features[j]
                                        if (cid === feat.conceptId) {
                                            featArr.push(feat)
                                        }
                                    }
                                    featArr.push(cid)
                                }
                            }
                            dispatch(setFeatures(featArr))
                        }
                    });
                } else {
                    navigate('/notfound404')
                }
            } else {
                navigate('/notfound404')
            }
        }
    }, [idoc, imgUrl, objIntIdx, annoIntIdx]);

    const setupTextHighlighting = (anno: Annotation, ranges: [number, number][], wFlags: boolean[]) => {
        let words = anno.tokens
        let selection = window.getSelection()
        if (selection && words.length > 0) {
            let anchor = selection.anchorNode
            let nfocus = selection.focusNode
            if (anchor && nfocus && nfocus.nodeType === 3 && anchor.nodeType === 3) {
                let startElem = anchor.parentElement
                let endElem = nfocus.parentElement
                if (startElem?.id === '' && startElem.parentElement) {
                    startElem = startElem.parentElement.parentElement
                }
                if (endElem?.id === '' && endElem.parentElement) {
                    endElem = endElem.parentElement.parentElement
                }
                let annoViewer = document.getElementById("annoViewer")
                if (startElem && endElem && annoViewer && startElem.id.startsWith("w") && endElem.id.startsWith("w")
                    && annoViewer.contains(startElem) && annoViewer.contains(endElem)) {
                    let substrStart = startElem.id.startsWith('ws') ? 2 : 1
                    let startWordIdx: number = parseInt(startElem.id.substring(substrStart))
                    substrStart = endElem.id.startsWith('ws') ? 2 : 1
                    let endWordIdx: number = parseInt(endElem.id.substring(substrStart))
                    let startOffset: number
                    let endOffset: number
                    if (startWordIdx === endWordIdx) {
                        for (let i = 0; i < ranges.length; i++) {
                            let range = ranges[i]
                            if (startWordIdx >= range[0] && startWordIdx <= range[1]) {
                                return
                            }
                        }
                        if (wFlags[startWordIdx]) {
                            markWords([startWordIdx])
                            selection.empty()
                        }
                        return
                    } else if (startWordIdx > endWordIdx) {
                        let temp: number = startWordIdx
                        startWordIdx = endWordIdx
                        endWordIdx = temp
                        startOffset = selection.focusOffset
                        endOffset = selection.anchorOffset
                    } else {
                        startOffset = selection.anchorOffset
                        endOffset = selection.focusOffset
                    }
                    let result: number[] = []
                    for (let i = startWordIdx; i < endWordIdx; i++) {
                        if (!wFlags[i]) {
                            return
                        }
                    }
                    for (let i = 0; i < ranges.length; i++) {
                        let range = ranges[i]
                        if (startWordIdx >= range[0] && endWordIdx <= range[1]) {
                            return
                        }
                    }

                    if (!wFlags[startWordIdx]) {
                        result.push(startWordIdx + 1)
                    } else if (startOffset <= 1) {
                        result.push(startWordIdx)
                    } else {
                        result.push(startWordIdx + 1)
                    }

                    if (!wFlags[endWordIdx]) {
                        result.push(endWordIdx)
                    } else if (endOffset === words[endWordIdx].length + 1) {
                        result.push(endWordIdx + 1)
                    } else {
                        result.push(endWordIdx)
                    }
                    if (result[1] > result[0]) {
                        markWords(result)
                        selection.empty()
                    }
                }
            }
        }
    }

    useEffect(() => {
        if (wordFlags && wordFlags.length > 0 && annotation && conceptRanges) {
            let listener = () => setupTextHighlighting(annotation, conceptRanges, wordFlags)
            document.addEventListener('mouseup', listener)
            return () => {
                document.removeEventListener('mouseup', listener)
            };
        }
    }, [annotation, wordFlags, conceptRanges]);

    const isNextDisabled = () => {
        if (idoc?.objects && objIntIdx !== undefined && annoIntIdx !== undefined) {
            let obj = idoc.objects[objIntIdx];
            return !obj.annotations || annoIntIdx >= obj.annotations.length - 1;
        } else {
            return true
        }
    }

    return (
        <Box height='100%'>
            <Box height='60%'
                 sx={{
                     p: 2, bgcolor: 'rgba(50, 50, 255, 0.08)',
                     border: '2px solid',
                     borderColor: 'divider',
                     position: 'relative'
                 }}>
                <Box ref={imgContainer} height='93%' sx={{
                    position: 'absolute', display: 'block',
                    left: '50%', transform: 'translateX(-50%)'
                }}>
                    {<canvas ref={canvasRef} style={{height: '100%'}}/>}
                    {showFeats && bboxs && bboxs.flat()}
                </Box>
            </Box>
            <Box height='32%' id="annoViewer"
                 sx={{
                     display: 'flex',
                     justifyContent: 'center',
                     alignItems: 'center',
                     bgcolor: 'rgba(50, 50, 255, 0.08)',
                     fontSize: '20px',
                     border: '2px solid',
                     borderColor: 'divider',
                     my: 1, px: 5,
                 }}>
                <Box>
                    {highlightedAnnotation}
                </Box>
            </Box>
            <Box sx={{display: 'flex', width: '100%'}}>
                <Button sx={{width: '50%'}} variant='outlined' disabled={annoIntIdx === undefined || annoIntIdx <= 0}
                        onClick={() => {
                            if (project && docId && objIntIdx !== undefined && annoIntIdx !== undefined) {
                                navigate(`/project/${encodeURIComponent(project.title)}/idoc/${docId}/${objIntIdx}/${annoIntIdx - 1}`)
                            }
                        }}>Previous</Button>
                <Button sx={{width: '50%'}} variant='outlined' disabled={isNextDisabled()}
                        onClick={() => {
                            if (project && docId && objIntIdx !== undefined && annoIntIdx !== undefined) {
                                navigate(`/project/${encodeURIComponent(project.title)}/idoc/${docId}/${objIntIdx}/${annoIntIdx + 1}`)
                            }
                        }}>Next</Button>
            </Box>
        </Box>
    )
}

export default AnnotationView
