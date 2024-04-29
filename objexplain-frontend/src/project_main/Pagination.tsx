import {ChangeEvent, FC, useEffect} from 'react';
import {Box, Button, Input, Typography} from "@mui/material";
import {useDispatch, useSelector} from "react-redux";
import './Pagination.css';
import {firstPage, lastPage, setPage} from "../reducers/mainPageSlice";


interface PaginationProps {
    pageText: string
    setPageText: Function
    toPrevPage: any
    toNextPage: any
}

const Pagination: FC<PaginationProps> = ({pageText, setPageText, toPrevPage, toNextPage}) => {
    const dispatch = useDispatch()

    // global state (redux)
    const page: number = useSelector((state: any) => state.mainPage.page);
    const maxPage: number = useSelector((state: any) => state.mainPage.maxPage);

    const toFirstPage = () => {
        dispatch(firstPage())
        setPageText('1')
    }

    const toLastPage = () => {
        if (maxPage !== undefined) {
            dispatch(lastPage())
            setPageText(maxPage.toString())
        }
    }

    const handlePageFieldChange = (event: ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
        event.stopPropagation();
        let value = event.target.value
        if (value.length > 0) {
            try {
                let newPage: number = parseInt(value);
                if (newPage < maxPage) {
                    dispatch(setPage(newPage))
                    setPageText(newPage.toString())
                }
            } catch (e) {
            }
        } else {
            setPageText('')
            dispatch(firstPage())
        }
    }

    let pageField = <Input fullWidth={false} value={pageText} size='small'
                           onChange={(e) => handlePageFieldChange(e)}
                           sx={{width: (page.toString().length * 12) + 'px', fontSize: '20px', mr: 1}}/>

    let prevPageDisable = page <= 1
    let nextPageDisable = maxPage !== undefined && page >= maxPage

    useEffect(() => {
        if (maxPage !== undefined) {
            toFirstPage()
        }
    }, [maxPage]);

    return (
        <Box sx={{display: 'flex', bottom: '5px', width: '99%'}}>
            <Button className='skip-button' variant={"contained"} sx={{backgroundColor: "primary", ml: 1,}}
                    onClick={toFirstPage} disabled={prevPageDisable}>
                <b>{'<<'}</b>
            </Button>
            <Button className='page-button' variant="contained" sx={{backgroundColor: "primary",}}
                    onClick={toPrevPage} disabled={prevPageDisable}><b>{'<'}</b></Button>
            <Box sx={{height: 'fit-content', margin: 'auto'}}>
                <Box sx={{display: 'flex', flexGrow: 100}} onBlur={(e) => {
                    e.preventDefault()
                    if (pageText.length === 0) {
                        setPageText('1')
                    }
                }}>
                    {pageField}
                    <Typography variant='h6' color='text.primary'>
                        {maxPage === undefined ? ' / 1' : ' / ' + maxPage}
                    </Typography>
                </Box>
            </Box>
            <Button className='page-button' variant="contained" sx={{backgroundColor: "primary",}}
                    onClick={toNextPage} disabled={nextPageDisable}>
                <b>{'>'}</b>
            </Button>
            <Button className='skip-button' variant={"contained"} sx={{backgroundColor: "primary"}}
                    onClick={toLastPage} disabled={nextPageDisable}>
                <b>{'>>'}</b>
            </Button>
        </Box>
    )
}

export default Pagination;
