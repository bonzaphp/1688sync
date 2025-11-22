import React, { useState, useMemo } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Toolbar,
  Typography,
  IconButton,
  Tooltip,
  Chip,
  LinearProgress,
  Checkbox,
  useTheme
} from '@mui/material';
import {
  FirstPage as FirstPageIcon,
  KeyboardArrowLeft,
  KeyboardArrowRight,
  LastPage as LastPageIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { visuallyHidden } from '@mui/utils';

export interface TableColumn<T = any> {
  id: string;
  label: string;
  minWidth?: number;
  width?: number;
  align?: 'left' | 'center' | 'right';
  format?: (value: any, row?: T) => string | React.ReactNode;
  sortable?: boolean;
  searchable?: boolean;
}

export interface DataTableAction {
  label: string;
  icon: React.ReactNode;
  onClick: (row: any) => void;
  disabled?: (row: any) => boolean;
  color?: 'inherit' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';
}

interface DataTableProps<T> {
  columns: TableColumn[];
  data: T[];
  loading?: boolean;
  totalCount?: number;
  page?: number;
  rowsPerPage?: number;
  onPageChange?: (page: number) => void;
  onRowsPerPageChange?: (rowsPerPage: number) => void;
  onSort?: (column: string, direction: 'asc' | 'desc') => void;
  onRefresh?: () => void;
  onExport?: () => void;
  onRowClick?: (row: T) => void;
  actions?: DataTableAction[] | ((row: T) => DataTableAction[]);
  getRowActions?: (row: T) => DataTableAction[];
  selection?: {
    selected: any[];
    onSelectionChange: (selected: any[]) => void;
  };
  emptyMessage?: string;
  title?: string;
}

function TablePaginationActions(props: {
  count: number;
  page: number;
  rowsPerPage: number;
  onPageChange: (
    event: React.MouseEvent<HTMLButtonElement>,
    newPage: number,
  ) => void;
}) {
  const theme = useTheme();
  const { count, page, rowsPerPage, onPageChange } = props;

  const handleFirstPageButtonClick = (
    event: React.MouseEvent<HTMLButtonElement>,
  ) => {
    onPageChange(event, 0);
  };

  const handleBackButtonClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    onPageChange(event, page - 1);
  };

  const handleNextButtonClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    onPageChange(event, page + 1);
  };

  const handleLastPageButtonClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    onPageChange(event, Math.max(0, Math.ceil(count / rowsPerPage) - 1));
  };

  return (
    <Box sx={{ flexShrink: 0, ml: 2.5 }}>
      <IconButton
        onClick={handleFirstPageButtonClick}
        disabled={page === 0}
        aria-label="first page"
      >
        <FirstPageIcon />
      </IconButton>
      <IconButton
        onClick={handleBackButtonClick}
        disabled={page === 0}
        aria-label="previous page"
      >
        <KeyboardArrowLeft />
      </IconButton>
      <IconButton
        onClick={handleNextButtonClick}
        disabled={page >= Math.ceil(count / rowsPerPage) - 1}
        aria-label="next page"
      >
        <KeyboardArrowRight />
      </IconButton>
      <IconButton
        onClick={handleLastPageButtonClick}
        disabled={page >= Math.ceil(count / rowsPerPage) - 1}
        aria-label="last page"
      >
        <LastPageIcon />
      </IconButton>
    </Box>
  );
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  loading = false,
  totalCount = data.length,
  page = 0,
  rowsPerPage = 20,
  onPageChange,
  onRowsPerPageChange,
  onSort,
  onRefresh,
  onExport,
  onRowClick,
  actions = [],
  getRowActions,
  selection,
  emptyMessage = '暂无数据',
  title
}: DataTableProps<T>) {
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const [orderBy, setOrderBy] = useState<string>('');
  const [selected, setSelected] = useState<any[]>(selection?.selected || []);

  const handleRequestSort = (
    event: React.MouseEvent<unknown>,
    property: string,
  ) => {
    const isAsc = orderBy === property && order === 'asc';
    const newOrder = isAsc ? 'desc' : 'asc';
    setOrder(newOrder);
    setOrderBy(property);
    onSort?.(property, newOrder);
  };

  const handleChangePage = (
    event: React.MouseEvent<HTMLButtonElement> | null,
    newPage: number,
  ) => {
    onPageChange?.(newPage);
  };

  const handleChangeRowsPerPage = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    onRowsPerPageChange?.(parseInt(event.target.value, 10));
  };

  const handleSelectAllClick = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      const newSelected = data.map((n) => n);
      setSelected(newSelected);
      selection?.onSelectionChange(newSelected);
    } else {
      setSelected([]);
      selection?.onSelectionChange([]);
    }
  };

  const handleClick = (event: React.MouseEvent<unknown>, row: T) => {
    const selectedIndex = selected.findIndex((item) => item.id === row.id);
    let newSelected: any[] = [];

    if (selectedIndex === -1) {
      newSelected = newSelected.concat(selected, row);
    } else if (selectedIndex === 0) {
      newSelected = newSelected.slice(1);
    } else if (selectedIndex === selected.length - 1) {
      newSelected = newSelected.slice(0, -1);
    } else if (selectedIndex > 0) {
      newSelected = [
        ...selected.slice(0, selectedIndex),
        ...selected.slice(selectedIndex + 1),
      ];
    }

    setSelected(newSelected);
    selection?.onSelectionChange(newSelected);
  };

  const isSelected = (id: number) => selected.findIndex((item) => item.id === id) !== -1;

  const sortedData = useMemo(() => {
    if (!orderBy) return data;

    return [...data].sort((a, b) => {
      const aValue = a[orderBy];
      const bValue = b[orderBy];

      if (aValue === null || aValue === undefined) return order === 'asc' ? 1 : -1;
      if (bValue === null || bValue === undefined) return order === 'asc' ? -1 : 1;

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return order === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return order === 'asc' ? aValue - bValue : bValue - aValue;
      }

      return 0;
    });
  }, [data, orderBy, order]);

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ width: '100%', mb: 2 }}>
        {(title || onRefresh || onExport || actions.length > 0) && (
          <Toolbar
            sx={{
              pl: { sm: 2 },
              pr: { xs: 1, sm: 1 },
              ...(title && {
                minHeight: 64,
              }),
            }}
          >
            {title && (
              <Typography
                sx={{ flex: '1 1 100%' }}
                variant="h6"
                id="tableTitle"
                component="div"
              >
                {title}
              </Typography>
            )}

            <Box sx={{ display: 'flex', gap: 1 }}>
              {onRefresh && (
                <Tooltip title="刷新">
                  <IconButton onClick={onRefresh} disabled={loading}>
                    <RefreshIcon />
                  </IconButton>
                </Tooltip>
              )}

              {onExport && (
                <Tooltip title="导出">
                  <IconButton onClick={onExport} disabled={loading}>
                    <DownloadIcon />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          </Toolbar>
        )}

        {loading && <LinearProgress />}

        <TableContainer>
          <Table
            sx={{ minWidth: 750 }}
            aria-labelledby="tableTitle"
            size="medium"
          >
            <TableHead>
              <TableRow>
                {selection && (
                  <TableCell padding="checkbox">
                    <Checkbox
                      color="primary"
                      indeterminate={selected.length > 0 && selected.length < data.length}
                      checked={data.length > 0 && selected.length === data.length}
                      onChange={handleSelectAllClick}
                      inputProps={{
                        'aria-label': 'select all desserts',
                      }}
                    />
                  </TableCell>
                )}

                {columns.map((headCell) => (
                  <TableCell
                    key={headCell.id}
                    align={headCell.align || 'left'}
                    padding={headCell.id === 'actions' ? 'checkbox' : 'normal'}
                    sortDirection={orderBy === headCell.id ? order : false}
                    style={{ minWidth: headCell.minWidth, width: headCell.width }}
                  >
                    {headCell.sortable !== false ? (
                      <TableSortLabel
                        active={orderBy === headCell.id}
                        direction={orderBy === headCell.id ? order : 'asc'}
                        onClick={(event) => handleRequestSort(event, headCell.id)}
                      >
                        {headCell.label}
                        {orderBy === headCell.id ? (
                          <Box component="span" sx={visuallyHidden}>
                            {order === 'desc' ? 'sorted descending' : 'sorted ascending'}
                          </Box>
                        ) : null}
                      </TableSortLabel>
                    ) : (
                      headCell.label
                    )}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>

            <TableBody>
              {sortedData.map((row, index) => {
                const isItemSelected = isSelected(row.id);
                const labelId = `enhanced-table-checkbox-${index}`;

                return (
                  <TableRow
                    hover
                    onClick={() => onRowClick?.(row)}
                    role="checkbox"
                    aria-checked={isItemSelected}
                    tabIndex={-1}
                    key={row.id}
                    selected={isItemSelected}
                    sx={{ cursor: onRowClick ? 'pointer' : 'default' }}
                  >
                    {selection && (
                      <TableCell padding="checkbox">
                        <Checkbox
                          color="primary"
                          checked={isItemSelected}
                          inputProps={{
                            'aria-labelledby': labelId,
                          }}
                        />
                      </TableCell>
                    )}

                    {columns.map((column) => {
                      const value = row[column.id];

                      if (column.id === 'actions') {
                        const rowActions = getRowActions ? getRowActions(row) : actions;
                        return (
                          <TableCell key={column.id} align={column.align || 'left'}>
                            <Box sx={{ display: 'flex', gap: 0.5 }}>
                              {(Array.isArray(rowActions) ? rowActions : []).map((action, actionIndex) => (
                                <Tooltip key={actionIndex} title={action.label}>
                                  <IconButton
                                    size="small"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      action.onClick(row);
                                    }}
                                    disabled={action.disabled?.(row)}
                                    color={action.color || 'inherit'}
                                  >
                                    {action.icon}
                                  </IconButton>
                                </Tooltip>
                              ))}
                            </Box>
                          </TableCell>
                        );
                      }

                      return (
                        <TableCell key={column.id} align={column.align || 'left'}>
                          {column.format ? column.format(value, row) : value}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })}

              {!loading && data.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={columns.length + (selection ? 1 : 0)}
                    align="center"
                    sx={{ py: 4 }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      {emptyMessage}
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          rowsPerPageOptions={[10, 20, 50, 100]}
          component="div"
          count={totalCount}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          ActionsComponent={TablePaginationActions}
          labelRowsPerPage="每页行数:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} 共 ${count}`}
        />
      </Paper>
    </Box>
  );
}

export default DataTable;