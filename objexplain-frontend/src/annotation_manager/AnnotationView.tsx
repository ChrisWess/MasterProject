import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest} from "../api/requests";
import {FC, useEffect, useMemo, useRef, useState} from "react";
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
    initVisibleFeatures,
    setAnnotation,
    setAnnotationIdx,
    setConceptRanges,
    setConceptSubs,
    setFeatures
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
    // TODO: load features with expanded concept?
    return await getRequest('visFeature/annotation', annoId)
}

const AnnotationView: FC = () => {
    const {projectName, docId, objIdx, annoIdx} = useParams();
    const context: any = useOutletContext();
    const imgContainer = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [hoverToggle, setHoverToggle] = useState<boolean>(true);
    const [selectedConcept, setSelectedConcept] = useState<number>();
    const [cColor, setColor] = useState<string>("black");
    const [wordFlags, setWordFlags] = useState<boolean[]>([]);
    const [markedWords, setMarkedWords] = useState<number[]>([]);
    const [markedWordsPrevColors, setPrevColors] = useState<any[]>([]);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const imgUrl: string | undefined = useSelector((state: any) => state.iDoc.imgUrl);
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);
    const annotation: Annotation | undefined = useSelector((state: any) => state.annotation.annotation);
    const featsVis: boolean[] | undefined = useSelector((state: any) => state.annotation.featuresVis);
    const showFeats: boolean = useSelector((state: any) => state.annotation.showFeatures);
    const features: VisualFeature[] | undefined = useSelector((state: any) => state.annotation.features);
    const conceptSubs: string[] | undefined = useSelector((state: any) => state.annotation.conceptSubstrings);
    const conceptRanges: [number, number][] | undefined = useSelector((state: any) => state.annotation.conceptRanges);
    const showConcepts: boolean = useSelector((state: any) => state.annotation.showConcepts);

    let objIntIdx = objIdx ? parseInt(objIdx) : undefined;
    let objId = idoc?.objects && objIntIdx !== undefined ? idoc.objects[objIntIdx]._id : undefined
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
                return features.map((feat, index) => {
                    if (featsVis[index]) {
                        let color = CONCEPT_COLORS[index % 10];
                        // Supply text only for first bbox (use the text part of the concept of current annotation)
                        return feat.bboxs!.map((bbox, idx) => {
                            let key = feat._id + '_' + idx;
                            if (idx === 0) {
                                return <Box key={key} position='absolute' border='solid 5px'
                                            borderColor={color}
                                            sx={{top: ratio * bbox.tlx - 5, left: ratio * bbox.tly - 5}}
                                            width={ratio * (bbox.brx - bbox.tlx) + 10}
                                            height={ratio * (bbox.bry - bbox.tly) + 10}
                                            onClick={() => {
                                            }}>
                                    <Typography color={color} sx={{fontSize: '14px', ml: '4px'}}>
                                        <b color={color}>{conceptSubs[index]}</b>
                                    </Typography>
                                </Box>
                            } else {
                                return <Box key={key} position='absolute' border='solid 5px' borderColor={color}
                                            sx={{top: ratio * bbox.tlx - 5, left: ratio * bbox.tly - 5}}
                                            width={ratio * (bbox.brx - bbox.tlx) + 10}
                                            height={ratio * (bbox.bry - bbox.tly) + 10}
                                            onClick={() => {
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
        if (markedWords.length === 1) {
            let prev = document.getElementById("w" + markedWords[0])
            if (prev) {  // && prev.classList.contains("wregular")
                prev.style.backgroundColor = markedWordsPrevColors[0]
            }
        } else if (markedWords.length === 2) {
            for (let i = markedWords[0]; i < markedWords[1]; i++) {
                let prev = document.getElementById("w" + i)
                if (prev) {  // && prev.classList.contains("wregular")
                    prev.style.backgroundColor = markedWordsPrevColors[i - markedWords[0]]
                }
            }
        }
    };

    const setNewConceptSelection = (value: any) => {
        clearPrevMarking()
        if (!value) {
            setSelectedConcept(undefined)
            setColor("black")
        } else if (typeof value === 'number') {
            setSelectedConcept(value)
            setColor(CONCEPT_COLORS[value])
        } else {
            let idx = parseInt(value.currentTarget.id.substring(1));
            setSelectedConcept(idx)
            setColor(CONCEPT_COLORS[idx])
        }
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
        if (markRange.length > 1 && markRange[0] + 1 < markRange[1]) {
            for (let i = markRange[0]; i < markRange[1]; i++) {
                let prev = document.getElementById("w" + i)
                if (prev) {
                    prevColors.push(getStyle(prev, "background-color"));
                    prev.style.backgroundColor = "deepskyblue"
                }
            }
            setMarkedWords(markRange)
        }
        setColor("deepskyblue")
    }

    const highlightedAnnotation = useMemo(() => {
        let buffer: ReactJSXElement[] = new Array<ReactJSXElement>()
        if (annotation && conceptRanges) {
            let tokens: string[] = annotation.tokens;
            let flags = []
            let currRange = 0;
            let idxStart = -1;
            let idxEnd = -1;
            if (conceptRanges && conceptRanges.length > currRange) {
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
                        if (markedWords.length != 0 && i >= markedWords[0] && i <= markedWords[1]) {
                            buffer.push(<abbr key={currentId} id={currentId}><Highlighted text={token}/></abbr>);
                        } else {
                            buffer.push(<abbr key={currentId} id={currentId}>{token}</abbr>);
                        }
                    } else {
                        if (markedWords.length != 0 && i >= markedWords[0] && i <= markedWords[1]) {
                            if (i == markedWords[0]) {
                                buffer.push(<abbr key={currentId} id={currentId} className="wregular"><Highlighted
                                    text={" " + token}/></abbr>);
                            } else if (i == markedWords[1]) {
                                buffer.push(<abbr key={currentId} id={currentId} className="wregular"><Highlighted
                                    text={" " + token}/></abbr>);
                            } else {
                                buffer.push(<abbr key={currentId} id={currentId} className="wregular"
                                                  style={{backgroundColor: "yellow"}}>{" " + token} </abbr>);
                            }
                        } else {
                            buffer.push(<abbr key={currentId} id={currentId} className="wregular">{" " + token}</abbr>)
                        }
                    }
                } else if (i === idxEnd) {
                    let id = 'w' + idxStart
                    let currentId = 'c' + currRange;
                    let id1 = "w" + idxEnd;
                    buffer.push(
                        <b key={currentId} id={currentId} onClick={setNewConceptSelection}>
                            {" "}
                            <abbr key={id + "-1"} id={id} className={"cr cr-" + currRange}
                                  style={{backgroundColor: CONCEPT_COLORS[currRange % 10]}}>
                                <a key={id + "-2"} id={id} href="">[</a>
                                <HoverBox
                                    word={tokens[idxStart]}
                                    conceptIdx={currRange}
                                    hovertoggle={hoverToggle}
                                    annotation={annotation}
                                    color={CONCEPT_COLORS[currRange % 10]}/>
                            </abbr>
                            {tokens.slice(idxStart + 1, idxEnd).map((elem, index) => (
                                <abbr key={'w' + (idxStart + index + 1) + "-1"}
                                      id={'w' + (idxStart + index + 1)}
                                      className={"cr cr-" + currRange}
                                      style={{backgroundColor: CONCEPT_COLORS[currRange % 10]}}>
                                    {" "}
                                    <HoverBox
                                        word={elem}
                                        conceptIdx={currRange}
                                        hovertoggle={hoverToggle}
                                        annotation={annotation}
                                        color={CONCEPT_COLORS[currRange % 10]}/>
                                </abbr>
                            ))}
                            <abbr key={id1 + "-1"} id={id1} className={"cr cr-" + currRange}
                                  style={{backgroundColor: CONCEPT_COLORS[currRange % 10]}}>
                                {" "}
                                <HoverBox
                                    word={tokens[idxEnd]}
                                    conceptIdx={currRange}
                                    hovertoggle={hoverToggle}
                                    annotation={annotation}
                                    color={CONCEPT_COLORS[currRange % 10]}/>
                                <a key={id1 + "-2"} id={id1} href="">]</a>
                                <sub key={id1 + "-3"} id={id1}>{currRange}</sub>
                            </abbr>
                        </b>)
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
            setWordFlags(flags);
        }
        return buffer
    }, [annotation, conceptRanges, markedWords])

    const extractConceptInfo = (anno: Annotation) => {
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
        dispatch(setConceptSubs(conceptStrings))
        dispatch(setConceptRanges(ranges))
    }

    const setupTextHighlighting = (anno: Annotation) => {
        document.addEventListener('mouseup', () => {
            let words = anno.tokens
            let selection = window.getSelection()
            if (selection && words.length > 0) {
                let anchor = selection.anchorNode
                let nfocus = selection.focusNode
                if (anchor && nfocus && !nfocus.hasChildNodes() && !anchor.hasChildNodes()) {
                    let startElem = anchor.parentElement
                    let endElem = nfocus.parentElement
                    let docView = document.getElementById("docView")
                    if (startElem && endElem && docView && startElem.id.startsWith("w") && endElem.id.startsWith("w") &&
                        docView.contains(startElem) && docView.contains(endElem)) {
                        let startWordIdx: number = parseInt(startElem.id.substring(1))
                        let endWordIdx: number = parseInt(endElem.id.substring(1))
                        let startOffset: number
                        let endOffset: number
                        if (startWordIdx === endWordIdx) {
                            startOffset = Math.min(selection.anchorOffset, selection.focusOffset)
                            endOffset = Math.max(selection.anchorOffset, selection.focusOffset)
                            let word: string = words[startWordIdx]
                            // offset needs to start at 1, because there is always a space at 0
                            if (startOffset <= 1 && wordFlags[startWordIdx] && endOffset === word.length + 1) {
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
                        let wordFlagsSlice: boolean[] = wordFlags.slice(startWordIdx, endWordIdx + 1)
                        for (let i = 1; i < wordFlagsSlice.length - 1; i++) {
                            if (!wordFlagsSlice[i]) {
                                return
                            }
                        }

                        if (!wordFlagsSlice[0]) {
                            result.push(startWordIdx + 1)
                        } else if (startOffset <= 1) {
                            result.push(startWordIdx)
                        } else {
                            result.push(startWordIdx + 1)
                        }

                        if (!wordFlagsSlice[wordFlagsSlice.length - 1]) {
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
        });
    }

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
                if (objId && annotations && annoIntIdx < annotations.length) {
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
                        extractConceptInfo(currAnno);
                        setupTextHighlighting(currAnno);
                    }
                    loadVisualFeatures(currAnno._id).then(data => {
                        if (data) {
                            let features = data.result
                            dispatch(setFeatures(features))
                            dispatch(initVisibleFeatures(features.length))
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
            <Box height='54%'
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
            <Box height='38%'
                 sx={{
                     display: 'flex',
                     justifyContent: 'center',
                     alignItems: 'center',
                     bgcolor: 'rgba(50, 50, 255, 0.08)',
                     fontSize: '20px',
                     borderColor: 'divider',
                     my: 1
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
