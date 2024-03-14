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
import {setObject, setObjectIdx} from "../reducers/objectSlice";
import {Annotation} from "../api/models/annotation";
import AnnotationControlPanel from "./AnnotationControl";
import {setAnnotation, setAnnotationIdx, setConceptSubs, setFeatures} from "../reducers/annotationSlice";
import {CONCEPT_COLORS} from "./FeatureView";
import {VisualFeature} from "../api/models/feature";
import {cropImage, loadDoc} from "../object_annotator/ObjectPage";
import {setTitle} from "../reducers/appBarSlice";
import {Label} from "../api/models/label";


export const loadVisualFeatures = async (annoId: string) => {
    // TODO: load features with expanded concept?
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
    const featsVis: boolean[] | undefined = useSelector((state: any) => state.annotation.featuresVis);
    const showFeats: boolean = useSelector((state: any) => state.annotation.showFeatures);
    const features: VisualFeature[] | undefined = useSelector((state: any) => state.annotation.features);
    const conceptSubs: string[] | undefined = useSelector((state: any) => state.annotation.conceptSubstrings);

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

    const extractConceptStrings = (anno: Annotation) => {
        let conceptStrings = []
        let currVal = -1
        let currString = ''
        for (let i = 0; i < anno.tokens.length; i++) {
            let maskVal = anno.conceptMask[i];
            if (maskVal >= 0) {
                if (currVal === maskVal) {
                    let token = anno.tokens[i];
                    if (token === ',' || token === '.') {
                        currString += token
                    } else {
                        currString += ' ' + token
                    }
                } else {
                    conceptStrings.push(currString)
                    currString = ''
                    currVal = -1
                }
            }
        }
        if (currString.length > 0) {
            conceptStrings.push(currString)
        }
        dispatch(setConceptSubs(conceptStrings))
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
                    dispatch(setTitle(`Annotation ${annoIntIdx + 1} of Object ${objectLabel?.name}`));
                    let newWidth = obj.brx - obj.tlx
                    let newHeight = obj.bry - obj.tly
                    cropImage(canvasRef, imgUrl, obj.tlx, obj.tly, newWidth, newHeight)
                    dispatch(setAnnotationIdx(annoIntIdx));
                    let currAnno = annotations[annoIntIdx];
                    if (!annotation || currAnno._id !== annotation._id) {
                        dispatch(setAnnotation(currAnno));
                        extractConceptStrings(currAnno);
                    }
                    loadVisualFeatures(currAnno._id).then(feature => dispatch(setFeatures(feature)));
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
                    {showFeats && bboxs}
                </Box>
            </Box>
            <Box height='40%'/>
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
