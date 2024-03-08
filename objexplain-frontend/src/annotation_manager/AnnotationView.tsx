import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest, loadImage} from "../api/requests";
import {FC, useEffect, useMemo, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setTitle} from "../reducers/appBarSlice";
import {setDoc, setImgUrl, setLabelMap} from "../reducers/idocSlice";
import {setProject} from "../reducers/mainPageSlice";
import {Button, Typography} from "@mui/material";
import {DetectedObject} from "../api/models/object";
import {Label} from "../api/models/label";
import {ImageDocument} from "../api/models/imgdoc";
import {getLabel} from "../document/ProjectIDocPage";
import ObjectControlPanel from "../object_annotator/ObjectControl";
import {mapLabels} from "../document/DocControl";
import {setFeatures, setObjectIdx} from "../reducers/objectSlice";


export const CONCEPT_COLORS = [
    '#9A6324',
    '#808000',
    '#469990',
    '#FFD8B1',
    '#DCBEFF',
    '#404040',
    '#AAFFC3',
    '#F032E6',
    '#6495ED',
    '#228B22',
]


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
    const labelsMap: [string, Label][] | undefined = useSelector((state: any) => state.iDoc.labelMap);
    const showFeats: boolean = useSelector((state: any) => state.object.showFeatures);
    const featsVis: boolean[] | undefined = useSelector((state: any) => state.object.featuresVis);

    /**
     * The concepts in the annotation are marked with the same color as the bounding boxes of the
     * visual features (of the object) to easily identify which feature displays which concept.
     */

    const generateFeatureBBoxs = () => {
        if (!!idoc) {
            let objs: DetectedObject[] = idoc.objects!;
            if (imgContainer.current && objs && objs.length > 0) {
                let imgHeight = imgContainer.current.offsetHeight
                if (imgHeight > 0) {
                    let ratio = imgHeight / idoc.height
                    return objs.filter((_, index) => featsVis && featsVis[index])
                        .map((obj, index) => {
                            let color = CONCEPT_COLORS[index % 10];
                            let label: Label | undefined = getLabel(labelsMap, obj);
                            return <Box key={obj._id} position='absolute' border='solid 5px' borderColor={color}
                                        sx={{top: ratio * obj.tlx - 5, left: ratio * obj.tly - 5}}
                                        width={ratio * (obj.brx - obj.tlx) + 10}
                                        height={ratio * (obj.bry - obj.tly) + 10}
                                        onClick={() => {
                                            if (project && idoc) {
                                                navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${index}`)
                                            }
                                        }}>
                                <Typography color={color} sx={{fontSize: '20px', ml: '4px'}}>
                                    <b color={color}>{!!label ? label.name : obj.labelId}</b>
                                </Typography>
                            </Box>
                        });
                }
            }
        }
    }

    const bboxs = useMemo(generateFeatureBBoxs, [idoc, imgUrl, labelsMap, featsVis])

    const loadProject = async () => {
        if (projectName) {
            return await getRequest('project/fromUser', encodeURIComponent(projectName!))
        } else {
            navigate('/notfound404')
        }
    }

    const loadDoc = async () => {
        if (docId) {
            return await getRequest('idoc', docId)
        }
        navigate('/notfound404')
    }

    const loadDocImage = async (imgDoc: ImageDocument) => {
        return await loadImage('idoc/img', imgDoc._id)
    }

    const loadFeatures = async (annotationId: string) => {
        return await getRequest('visFeature/annotation', annotationId)
    }

    useEffect(() => {
        if (!project) {
            loadProject().then(projectData => projectData && dispatch(setProject(projectData.result)))
        }
        if (idoc) {
            dispatch(setTitle(idoc.name));
        } else {
            loadDoc().then(idocData => {
                if (idocData) {
                    dispatch(setDoc(idocData.result));
                    dispatch(setTitle(idocData.result.name));
                    loadDocImage(idocData.result).then(file => {
                        file && dispatch(setImgUrl(file))
                    });
                }
            })
        }
        context.setControlPanel(<ObjectControlPanel/>)
    }, []);

    useEffect(() => {
        if (!labelsMap) {
            mapLabels(idoc).then(lm => lm && dispatch(setLabelMap(lm)));
        }
        if (objIdx && annoIdx) {
            let oidx = parseInt(objIdx);
            let aidx = parseInt(annoIdx);
            if (idoc && idoc.objects) {
                if (oidx >= 0 && aidx >= 0 && oidx < idoc.objects.length) {
                    let annotations = idoc.objects[oidx].annotations;
                    if (annotations && aidx < annotations.length) {
                        dispatch(setObjectIdx(oidx));
                        loadFeatures(annotations[aidx]._id).then(features => dispatch(setFeatures(features)));
                    } else {
                        navigate('/notfound404')
                    }
                } else {
                    navigate('/notfound404')
                }
            }
        } else {
            navigate('/notfound404')
        }
    }, [idoc]);

    return (
        <Box height='100%'>
            <Box height='94%'
                 sx={{
                     p: 2, bgcolor: 'rgba(50, 50, 255, 0.08)',
                     border: '2px solid',
                     borderColor: 'divider',
                     position: 'relative'
                 }}>
                <Box ref={imgContainer} height='96%' sx={{
                    position: 'absolute', display: 'block',
                    left: '50%', transform: 'translateX(-50%)'
                }}>
                    {imgUrl &&
                        <canvas ref={canvasRef} style={{height: '100%'}}/>}
                    {showFeats && bboxs}
                </Box>
            </Box>
            <Box sx={{display: 'flex', width: '100%'}}>
                <Button sx={{width: '50%'}} variant='outlined'>Previous</Button>
                <Button sx={{width: '50%'}} variant='outlined'>Next</Button>
            </Box>
        </Box>
    )
}

export default AnnotationView
