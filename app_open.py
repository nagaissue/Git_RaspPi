import pandas as pd
from dash import Dash, dash_table, dcc, callback, Output, Input, html
import plotly.express as px

# データの読み込み
df = pd.read_csv("label.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp", ascending=True)
df["timestamp_str"] = df["timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S')

# --- 修正点: 月ごとの合計値算出ロジック ---
df_monthly = df.copy()
# 月ラベルを作成
df_monthly['month'] = df_monthly['timestamp'].dt.to_period('M').astype(str)

# 数値列とグループキー('month')だけを先に抽出してからグループ化
num_cols = df_monthly.select_dtypes(include=['number']).columns.tolist()
monthly_summary = df_monthly.groupby('month')[num_cols].sum().reset_index()

# グラフ用にデータを整形
monthly_melted = monthly_summary.melt(id_vars='month', var_name='Nutrient', value_name='Total Value')

# カラーリングの基準値設定
thresholds = {
    'energy': 300, 'protein': 10, 'fat': 10, 'carb': 40, 'salt': 2.0
}

# --- グラフの事前作成と設定 ---
fig_monthly=px.bar(
    monthly_melted, 
    x='month', 
    y='Total Value', 
    color='Nutrient', 
    barmode='group',
    title="月ごとの項目別合計値推移",
    color_discrete_sequence=px.colors.qualitative.Pastel, # 少し色を柔らかく
    text_auto='.1f'
)
fig_monthly.update_layout(dragmode=False)

app = Dash(__name__)
# デプロイ用のインスタンス定義
server = app.server

app.layout = html.Div([
    html.H1("栄養成分表示ダッシュボード", style={"textAlign": "center"}),

    # 月ごとの合計棒グラフ
    html.Div([
        dcc.Graph(
            id="monthly_summary_graph",
            figure=fig_monthly
        )
    ], style={"padding": "20px", "backgroundColor": "#f8f9fa", "borderRadius": "10px", "marginBottom": "20px"}),

    # データテーブル
    dash_table.DataTable(
        id="data_table",
        columns=[{"name": i, "id": i} for i in df.columns if i != "timestamp_str"],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
        style_data_conditional=[
            {
                'if': {
                    'column_id': col,
                    'filter_query': f'{{{col}}} >= {val}'
                },
                'backgroundColor': '#FFEBEE',
                'color': '#C62828',
                'fontWeight': 'bold'
            } for col, val in thresholds.items()
        ]
    ),
    
    html.Div([
        html.Div([
            html.Label("表示する成分:"),
            dcc.Dropdown(
                options=[{"label": k, "value": k} for k in thresholds.keys()],
                value="energy",
                id="nutrient_selector",
                style={"width": "200px"}
            ),
        ], style={"display": "inline-block", "marginRight": "40px"}),
        
        html.Div([
            html.Label("数値の並び替え (個別データ):"),
            dcc.RadioItems(
                options=[{"label": "大きい順", "value": "desc"}, {"label": "小さい順", "value": "asc"}],
                value="desc",
                id="value_sort_type",
                inline=True
            ),
        ], style={"display": "inline-block"}),

        html.Div([
            html.Label("表示範囲 (行数):"),
            dcc.RangeSlider(
                id="range_slider",
                min=0, max=len(df), step=1, value=[0, 10],
                marks={i: str(i) for i in range(0, len(df) + 1, 10)}
            ),
        ], style={"marginTop": "20px"}),
    ], style={"padding": "20px", "border": "1px solid #ddd", "borderRadius": "5px", "margin": "20px 0"}),
    
    # 個別データの時系列グラフ
    html.Div([
        dcc.Graph(figure={}, id="nutrition_graph")
    ], style={"overflowX": "auto"}) 
])

@callback(
    Output("nutrition_graph", "figure"),
    Output("data_table", "data"),
    Input("nutrient_selector", "value"),
    Input("value_sort_type", "value"),
    Input("range_slider", "value")
)
def update_dashboard(selected_nutrient, sort_order, range_val):
    is_ascending = (sort_order == "asc")
    df_sorted = df.sort_values(selected_nutrient, ascending=is_ascending)
    df_sliced = df_sorted.iloc[range_val[0]:range_val[1]]
    
    min_width = max(800, len(df_sliced) * 60)
    fig = px.bar(
        df_sliced, x="timestamp_str", y=selected_nutrient,
        title=f"{selected_nutrient} の個別データ並び替え",
        labels={"timestamp_str": "記録時刻", selected_nutrient: f"{selected_nutrient} 量"}
    )
    fig.update_layout(width=min_width, bargap=0.3, dragmode=False)
    
    return fig, df_sliced.to_dict("records")

if __name__ == '__main__':
    app.run(host="0.0.0.0")
