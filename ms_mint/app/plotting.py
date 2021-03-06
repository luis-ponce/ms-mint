import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from matplotlib import pyplot as plt

import seaborn as sns

plt.rcParams['figure.autolayout'] = False
sns.set_context('paper')


from . import tools as T


_label='Plotting'

_kinds = ['bar', 'violin', 'box', 'count', 'boxen', 'scatter', 'line', 'strip', 'swarm', 'point']

kind_options = [{'value': x, 'label': x.capitalize()} for x in _kinds]

options = [
    {'label': 'Rotate x-ticks', 'value': 'rot-x-ticks'},
    {'label': 'Share x-axis', 'value': 'share-x'},
    {'label': 'Share y-axes', 'value': 'share-y'},
    {'label': 'Scientific notation', 'value': 'sci'},
    {'label': 'Logarithmic x-scale', 'value': 'log-x'},
    {'label': 'Logarithmic y-scale', 'value': 'log-y'},
    {'label': 'High Quality', 'value': 'HQ'},
    {'label': 'Don\'t dodge', 'value': 'no-dodge'}
]

_layout = html.Div([
    html.H3(_label),

    dcc.Input(id='plot-fig-height', placeholder='Figure facet height x', value=2.5, type="number"),
    dcc.Input(id='plot-fig-aspect', placeholder='Figure aspect ratio', value=1, type="number"),
    dcc.Input(id='plot-title', placeholder='Title', value=None),
    dcc.Dropdown(id='plot-kind', options=kind_options, value='bar'),

    dcc.Dropdown(id='plot-x', options=[], value=None, placeholder='X'),
    dcc.Dropdown(id='plot-y', options=[], value='peak_max', placeholder='Y'),
    dcc.Dropdown(id='plot-hue', options=[], value=None, placeholder='Color'),
    dcc.Dropdown(id='plot-col', options=[], value=None, placeholder='Columns'),
    dcc.Dropdown(id='plot-row', options=[], value=None, placeholder='Rows'),
    dcc.Dropdown(id='plot-style', options=[], value=None, placeholder='Style'),
    dcc.Dropdown(id='plot-size', options=[], value=None, placeholder='Size'),

    html.Label('Column wrap:'),
    dcc.Slider(id='plot-col-wrap', step=1, min=0, max=30, value=0),
    dcc.Dropdown(id='plot-options', value=['sci'], options=options, multi=True), 

    html.Button('Update', id='plot-update'),

    dcc.Loading( 
        html.Div(id='plot-figures',
         style={'margin': 'auto',
                'marginTop': '10%',
                'text-align': 'center',
                'maxWidth': '100%',
                'minHeight': '300px'}) )

])

_ouptuts = html.Div([])

def layout():
    return _layout


def callbacks(app, fsc, cache):

    @app.callback(
        Output('plot-x', 'options'),
        Output('plot-y', 'options'),
        Output('plot-col', 'options'),
        Output('plot-row', 'options'),
        Output('plot-hue', 'options'),
        Output('plot-size', 'options'),
        Output('plot-style', 'options'),
        Input('ana-secondary-tab', 'value'),
        State('wdir', 'children')
    )
    def fill_options(tab, wdir):
        if tab != _label: raise PreventUpdate
        results = T.get_complete_results( wdir )
        results = results.dropna(axis=1, how='all')
        cols = results.columns
        options = [{'value': x, 'label': x} for x in cols]
        return [options]*7

    @app.callback(
        Output('plot-figures', 'children'),
        Input('plot-update', 'n_clicks'),
        State('plot-kind', 'value'),
        State('plot-fig-height', 'value'),
        State('plot-fig-aspect', 'value'),
        State('plot-x', 'value'),
        State('plot-y', 'value'),
        State('plot-hue', 'value'),       
        State('plot-col', 'value'),
        State('plot-row', 'value'),
        State('plot-col-wrap', 'value'),
        State('plot-style', 'value'),
        State('plot-size', 'value'),
        State('plot-title', 'value'),
        State('ana-file-types', 'value'),
        State('ana-peak-labels-include', 'value'),
        State('ana-peak-labels-exclude', 'value'),
        State('ana-ms-order', 'value'), 
        State('plot-options', 'value'),
        State('wdir', 'children')
    )
    def create_figure(n_clicks, kind, height, aspect, x, y, hue, 
            col, row, col_wrap, style, size, title, file_types, 
            include_labels, exclude_labels, 
            ms_order, options, wdir):

        if n_clicks is None: raise PreventUpdate
        if col_wrap == 0: col_wrap = None
        if col is None and row is None: col_wrap=None
        if height is None: height = 2.5
        if aspect is None: aspect = 1

        # With hue both x and y have to be set.
        if (hue is not None) and (None in [x,y]):
            if x is None: x = hue
            if y is None: y = hue

        height = min(float(height), 100)
        height = max(height, 1)
        aspect = max(.01, float(aspect))
        aspect = min(aspect, 100)
        
        df = T.get_complete_results( wdir, include_labels=include_labels, 
                    exclude_labels=exclude_labels, file_types=file_types )

        df = df[(df.peak_n_datapoints>0) & (df.peak_max>0)]

        df = df.sort_values([ i for i in [col, row, hue, x, y, style, size] if i is not None])

        if hue is not None: df = df[df[hue].notna()]

        n_c, n_r = 1, 1
        if col is not None:
            n_c = len(df[col].drop_duplicates())
        if row is not None:
            n_r = len(df[row].drop_duplicates())
        
        if (n_c is not None) and (col_wrap is not None):
            n_c = n_c // col_wrap
            n_r = n_c % col_wrap

        if hue is not None and ((x is None) and (y is None)):
            x = hue

        if kind in ['scatter', 'line']:
            plot_func = sns.relplot
            kwargs = dict(facet_kws=dict(
                            sharex='share-x' in options,
                            sharey='share-y' in options,
                            legend_out=True
                          ),
                          style=style,
                          size=size
                     )
        else:
            plot_func = sns.catplot
            kwargs=dict(
                sharex='share-x' in options,
                sharey='share-y' in options,
                dodge='no-dodge' not in options,
                facet_kws=dict(legend_out=True)
            )

        g = plot_func(
                x=x, 
                y=y,
                hue=hue, 
                col=col, 
                row=row, 
                col_wrap=col_wrap,
                data=df, 
                kind=kind,
                height=height, 
                aspect=aspect,
                **kwargs
                )

        g.fig.subplots_adjust(top=0.9)
        g.set_titles(col_template="{col_name}", row_template="{row_name}", y=1.05)
        
        if 'log-x' in options:
            g.set(xscale="log")
        if 'log-y' in options:
            g.set(yscale="log")

        notation = 'sci' if 'sci' in options else 'plain'
        for ax in g.axes.flatten():
            try:
                ax.ticklabel_format(style=notation, scilimits=(0,0), axis='x')
            except:
                pass
            try:
                ax.ticklabel_format(style=notation, scilimits=(0,0), axis='y')
            except:
                pass            


        if 'rot-x-ticks' in options:
            g.set_xticklabels(rotation=90)

        if title is not None: g.fig.suptitle(title, y=1.01)

        g.tight_layout(w_pad=0)
       
        #try:
        #    g.legend.set_bbox_to_anchor((1.2, 0.7))
        #except:
        #    pass

        src = T.fig_to_src(dpi=300 if 'HQ' in options else None)

        return html.Img(src=src, style={'maxWidth': '80%'})