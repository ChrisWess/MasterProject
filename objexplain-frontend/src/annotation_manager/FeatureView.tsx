import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest, loadImage} from "../api/requests";
import {FC, useEffect, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setTitle} from "../reducers/appBarSlice";
import {setDoc} from "../reducers/idocSlice";
import {setProject} from "../reducers/mainPageSlice";
import {ImageDocument} from "../api/models/imgdoc";
import {setObjectIdx} from "../reducers/objectSlice";
import {Annotation} from "../api/models/annotation";
import AnnotationControlPanel from "./AnnotationControl";
import {setAnnotation, setAnnotationIdx, setFeatures, setObjImgUrl} from "../reducers/annotationSlice";


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


const FeatureView: FC = () => {
    const {projectName, docId, objIdx, annoIdx} = useParams();
    const context: any = useOutletContext();
    const imgContainer = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const annotation: Annotation | undefined = useSelector((state: any) => state.annotation.annotation);
    const objImgUrl: string | undefined = useSelector((state: any) => state.annotation.objImgUrl);
    const showFeats: boolean = useSelector((state: any) => state.annotation.showFeatures);
    const featsVis: boolean[] | undefined = useSelector((state: any) => state.annotation.featuresVis);

    let objIntIdx = objIdx ? parseInt(objIdx) : undefined;
    let objId = idoc?.objects && objIntIdx !== undefined ? idoc.objects[objIntIdx]._id : undefined
    let annoIntIdx = annoIdx ? parseInt(annoIdx) : undefined;

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

    const loadVisualFeatures = async (annoId: string) => {
        return await getRequest('visFeature/annotation', annoId)
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
                    let doc = idocData.result;
                    dispatch(setDoc(doc));
                    dispatch(setTitle(doc.name));
                }
            })
        }
        context.setControlPanel(<AnnotationControlPanel/>)
    }, []);

    useEffect(() => {
        if (idoc?.objects && objIntIdx && annoIntIdx && objIntIdx >= 0 && annoIntIdx >= 0 && objIntIdx < idoc.objects.length) {
            let annotations = idoc.objects[objIntIdx].annotations;
            if (objId && annotations && annoIntIdx < annotations.length) {
                dispatch(setObjectIdx(objIntIdx));
                dispatch(setAnnotationIdx(annoIntIdx));
                let currAnno = annotations[annoIntIdx];
                if (!annotation || currAnno._id !== annotation._id) {
                    dispatch(setAnnotation(currAnno));
                }
                loadVisualFeatures(currAnno._id).then(features => dispatch(setFeatures(features)));
                loadObjectImage(objId).then(file => {
                    file && dispatch(setObjImgUrl(file))
                });
            } else {
                navigate('/notfound404')
            }
        } else {
            navigate('/notfound404')
        }
    }, [idoc]);

    return (
        <Box height='100%'>

        </Box>
    )
}

export default FeatureView
