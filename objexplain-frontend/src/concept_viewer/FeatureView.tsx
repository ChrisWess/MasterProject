import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest, loadImage} from "../api/requests";
import {FC, RefObject, useCallback, useEffect, useMemo, useRef, useState} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setDoc} from "../reducers/idocSlice";
import {setProject} from "../reducers/mainPageSlice";
import {ImageDocument} from "../api/models/imgdoc";
import {setObject, setObjectIdx} from "../reducers/objectSlice";
import {Annotation} from "../api/models/annotation";
import {setAnnotation, setAnnotationIdx} from "../reducers/annotationSlice";
import FeatureControlPanel from "./FeatureControl";
import * as d3 from "d3";
import {ZoomBehavior} from "d3";
import FeatureAnnotator from "./FeatureAnnotator";
import {DetectedObject} from "../api/models/object";
import {setConceptIdx} from "../reducers/featureSlice";


const FeatureView: FC = () => {
    const {projectName, docId, objIdx, annoIdx, conceptIdx} = useParams();
    const context: any = useOutletContext();
    const svgRef: RefObject<SVGSVGElement> = useRef<SVGSVGElement>(null);
    const [objImgUrl, setObjImgUrl] = useState<string>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);
    const annotation: Annotation | undefined = useSelector((state: any) => state.annotation.annotation);

    let objIntIdx = objIdx ? parseInt(objIdx) : undefined;
    let objId = idoc?.objects && objIntIdx !== undefined ? idoc.objects[objIntIdx]._id : undefined
    let annoIntIdx = annoIdx ? parseInt(annoIdx) : undefined;
    let conceptIntIdx = conceptIdx ? parseInt(conceptIdx) : undefined;

    const zoom: ZoomBehavior<SVGSVGElement, unknown> = useMemo(() =>
        d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.5, 5]), []);

    const resetZoom = useCallback(() => {
        const svg = d3.select<SVGSVGElement, unknown>(svgRef.current!);
        svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
    }, [zoom, svgRef])

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

    const loadObjectImage = async (objId: string) => {
        return await loadImage('object/img', objId)
    }

    useEffect(() => {
        if (!project) {
            loadProject().then(projectData => projectData && dispatch(setProject(projectData.result)))
        }
        if (!idoc) {
            loadDoc().then(idocData => {
                if (idocData) {
                    dispatch(setDoc(idocData.result));
                }
            })
        }
        context.setControlPanel(<FeatureControlPanel resetZoomCallback={resetZoom}/>)
    }, []);

    useEffect(() => {
        if (idoc?.objects && objIntIdx !== undefined && annoIntIdx !== undefined && conceptIntIdx !== undefined) {
            if (objIntIdx >= 0 && annoIntIdx >= 0 && conceptIntIdx >= 0 && objIntIdx < idoc.objects.length) {
                let annotations = idoc.objects[objIntIdx].annotations;
                if (objId && annotations && annoIntIdx < annotations.length) {
                    dispatch(setObjectIdx(objIntIdx));
                    if (!detObj || detObj._id !== objId) {
                        dispatch(setObject(idoc.objects[objIntIdx]));
                    }
                    dispatch(setAnnotationIdx(annoIntIdx));
                    let currAnno = annotations[annoIntIdx];
                    if (!annotation || currAnno._id !== annotation._id) {
                        dispatch(setAnnotation(currAnno));
                    }
                    // loadVisualFeatures(currAnno._id).then(features => dispatch(setFeatures(features)));
                    loadObjectImage(objId).then(file => {
                        file && setObjImgUrl(file)
                    });
                    if (conceptIntIdx < currAnno.conceptIds.length)
                        dispatch(setConceptIdx(conceptIntIdx))
                } else {
                    navigate('/notfound404')
                }
            } else {
                navigate('/notfound404')
            }
        }
    }, [idoc, objIntIdx, annoIntIdx, conceptIntIdx]);

    return (
        <Box height='100%'>
            <FeatureAnnotator objImgUrl={objImgUrl ? objImgUrl : ''} svgRef={svgRef} zoom={zoom} height={780}/>
        </Box>
    )
}

export default FeatureView
