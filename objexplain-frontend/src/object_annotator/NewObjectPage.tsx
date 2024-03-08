import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {getRequest, loadImage} from "../api/requests";
import {FC, useEffect, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setProject} from "../reducers/mainPageSlice";
import ObjectControlPanel from "./ObjectControl";
import {ImageDocument} from "../api/models/imgdoc";
import {setDoc, setImgUrl} from "../reducers/idocSlice";


const NewObjectPage: FC = () => {
    const {projectName, docId} = useParams();
    const context: any = useOutletContext();
    const imgContainer = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const imgUrl: string | undefined = useSelector((state: any) => state.iDoc.imgUrl);

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

    useEffect(() => {
        if (!project) {
            loadProject().then(projectData => projectData && dispatch(setProject(projectData.result)))
        }
        if (!idoc) {
            loadDoc().then(idocData => {
                if (idocData) {
                    dispatch(setDoc(idocData.result));
                    loadDocImage(idocData.result).then(file => {
                        file && dispatch(setImgUrl(file))
                    });
                }
            })
        }
        context.setControlPanel(<ObjectControlPanel/>)
    }, []);

    return (
        <Box height='100%'>

        </Box>
    )
}

export default NewObjectPage
