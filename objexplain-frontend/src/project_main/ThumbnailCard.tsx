import {FC, MouseEvent, useState} from 'react';
import {useDispatch, useSelector} from "react-redux";
import {Card, CardActions, CardContent, CardProps, Typography} from "@mui/material";
import {useNavigate} from "react-router-dom";
import {getRequest, putRequest} from "../api/requests";
import Tooltip from "@mui/material/Tooltip";
import {ProjectStats} from "../api/models/project";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import {setMaxPage} from "../reducers/mainPageSlice";
import {clearDoc, disableAnnoMode} from "../reducers/idocSlice";


interface ThumbnailCardProps {
    docId: string
    name: string
    data: string
    setSelectedDoc: Function
    setRenameAction: Function
    setRemoveDocAction: Function
}

const ThumbnailCard: FC<ThumbnailCardProps & CardProps> = ({
                                                               docId, name, data, setSelectedDoc,
                                                               setRenameAction, setRemoveDocAction,
                                                               ...props
                                                           }) => {
    const [docName, setDocName] = useState<string>(name);
    const [contextMenu, setContextMenu] = useState<{ mouseX: number; mouseY: number } | null>(null);

    const handleContextMenu = (event: MouseEvent) => {
        event.preventDefault();
        setContextMenu(contextMenu === null ? {mouseX: event.clientX + 2, mouseY: event.clientY - 6} : null);
    };

    const handleMenuClose = () => {
        setContextMenu(null);
    };

    const navigate = useNavigate();
    const dispatch = useDispatch();

    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);

    const handleClickImage = (docId: string) => {
        const func: any = async () => {
            const data = await getRequest('idoc', docId)
            if (data) {
                dispatch(disableAnnoMode());
                dispatch(clearDoc());
                navigate("idoc/" + docId);
            }
        }
        return func
    }

    const renameDocOption = () => {
        return async (name: string) => {
            const data = await putRequest('idoc/rename', {docId: docId, docName: name})
            if (data) {
                setDocName(name)
            }
            handleMenuClose()
        }
    }

    const removeDocOption = () => {
        return async () => {
            if (project) {
                const data = await putRequest('project/idoc', {docId: docId, projectId: project._id})
                if (data) {
                    dispatch(setMaxPage(undefined))
                }
                handleMenuClose()
            }
        }
    }

    return (
        <>
            <Card
                sx={{
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    px: 0, pt: 0, m: 0.5,
                    width: 230,
                    height: 253,
                    bgcolor: 'rgba(150, 50, 255, 0.06)',
                }} onContextMenu={handleContextMenu} {...props}>
                <CardContent sx={{m: 0, px: 1.8, pt: 2, pb: 0}}>
                    <img alt="thumbnail" onClick={handleClickImage(docId)}
                         src={`data:image/png;base64,${data}`}
                         width={200} style={{cursor: 'pointer'}}/>
                </CardContent>
                <CardActions sx={{px: 1.5, py: 0}}>
                    {docName.length >= 24 ?
                        <Tooltip title={docName}>
                            <Typography onClick={() => {
                                navigate("idoc/" + docId)
                            }} sx={{cursor: 'pointer'}}>{docName.substring(0, 21) + '...'}</Typography>
                        </Tooltip> :
                        <Typography onClick={() => {
                            navigate("idoc/" + docId)
                        }} sx={{cursor: 'pointer'}}>{docName}</Typography>
                    }
                </CardActions>
            </Card>

            <Menu open={contextMenu !== null} onClose={handleMenuClose} anchorReference="anchorPosition"
                  anchorPosition={contextMenu !== null ? {
                      top: contextMenu.mouseY,
                      left: contextMenu.mouseX
                  } : undefined}>
                <MenuItem onClick={async () => {
                    await navigator.clipboard.writeText(docName);
                    handleMenuClose()
                }}>Copy Name</MenuItem>
                <MenuItem onClick={() => {
                    handleMenuClose()
                    setSelectedDoc(docName)
                    setRenameAction(renameDocOption)
                }}>Rename</MenuItem>
                <MenuItem onClick={() => {
                    handleMenuClose()
                    setSelectedDoc(docName)
                    setRemoveDocAction(removeDocOption)
                }}>Remove Document</MenuItem>
            </Menu>
        </>
    )
}

export default ThumbnailCard;
