# Forest Cover Classification - Streamlit Web Application

A comprehensive web application built with Streamlit for interacting with the Forest Cover Classification ML pipeline.

## 🌟 Features

### 🏠 Home Page
- Welcome overview with project information
- Quick stats and model information
- Navigation to different sections

### 🔮 Prediction Interface
- **Single Prediction**: Interactive form for individual predictions
- **Batch Prediction**: Process multiple samples at once
- **CSV Upload**: Upload and process CSV files with predictions
- Real-time prediction results with forest cover type mapping

### 📈 Analytics & Visualization
- Interactive charts and graphs
- Feature correlation analysis
- Data distribution visualizations
- Cover type distribution analysis

### 📊 Model Information
- Model metadata display
- Feature information
- Performance metrics
- Direct links to MLflow UI

### 🔧 Settings
- API configuration
- Display preferences
- Connection status

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Running ML pipeline services (inference, MLflow)

### Running the Application

1. **Build and start the Streamlit service:**
   ```bash
   docker compose up -d streamlit
   ```

2. **Access the application:**
   Open your browser and navigate to `http://localhost:8501`

3. **Verify all services are running:**
   ```bash
   docker compose ps
   ```

## 🎯 Usage Guide

### Making Predictions

#### Single Prediction
1. Navigate to the "🔮 Predict" page
2. Fill in the required fields in the "📝 Single Prediction" tab
3. Click "🔮 Predict Forest Cover Type"
4. View the prediction result with forest cover type

#### Batch Prediction
1. Go to the "📊 Batch Prediction" tab
2. Edit the sample data in the table
3. Add or remove rows as needed
4. Click "🔮 Predict All Samples"
5. View results and download if needed

#### CSV Upload
1. Navigate to the "📁 Upload CSV" tab
2. Upload a CSV file with the required columns
3. Click "🔮 Predict All Rows"
4. Download the results with predictions

### Required CSV Format

The CSV file should contain the following columns:

```csv
elevation,aspect,slope,horizontal_distance_to_hydrology,vertical_distance_to_hydrology,horizontal_distance_to_roadways,hillshade_9am,hillshade_noon,hillshade_3pm,horizontal_distance_to_fire_points,wilderness_area,soil_type
2596,51,3,258,0,510,211,232,148,6279,Rawah,C7745
3052,80,4,170,38,85,225,232,142,716,Rawah,C7201
```

### Forest Cover Types

The model predicts the following forest cover types:

- **0**: Spruce/Fir
- **1**: Lodgepole Pine
- **2**: Ponderosa Pine
- **3**: Cottonwood/Willow
- **4**: Aspen
- **5**: Douglas-fir
- **6**: Krummholz

## 🔧 Configuration

### Environment Variables

- `INFERENCE_API_URL`: URL of the inference API service (default: `http://inference:8000`)
- `MLFLOW_URL`: URL of the MLflow tracking server (default: `http://mlflow:5000`)
- `APP_TITLE`: Application title (default: `Forest Cover Classification`)
- `APP_ICON`: Application icon (default: `🌲`)

### Customization

The application can be customized by modifying:

1. **Configuration**: Update `config.py` for feature definitions and ranges
2. **Styling**: Modify the CSS in `main.py` for custom themes
3. **Features**: Add new pages or functionality in the main application

## 📊 Data Visualization

The application includes several interactive visualizations:

- **Pie Charts**: Cover type distribution
- **Scatter Plots**: Feature relationships (elevation vs slope)
- **Correlation Matrix**: Feature correlation heatmap
- **Bar Charts**: Prediction results distribution

## 🔍 Troubleshooting

### Common Issues

1. **API Connection Error**
   - Ensure the inference service is running
   - Check the API URL configuration
   - Verify network connectivity between services

2. **Prediction Errors**
   - Verify input data format
   - Check data type requirements (integers for numeric features)
   - Ensure all required fields are provided

3. **CSV Upload Issues**
   - Check CSV format matches requirements
   - Verify column names are correct
   - Ensure data types are compatible

### Health Checks

The application includes health checks for:
- API connectivity
- Model availability
- Data validation

## 🛠️ Development

### Project Structure

```
services/streamlit/
├── app/
│   └── main.py          # Main application file
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
└── README.md           # This file
```

### Adding New Features

1. **New Pages**: Add new page functions and update the navigation
2. **New Visualizations**: Use Plotly for interactive charts
3. **API Integration**: Extend the `ForestCoverApp` class
4. **Configuration**: Update `config.py` for new settings

### Testing

```bash
# Test the application locally
streamlit run app/main.py

# Test API connectivity
curl http://localhost:8000/health
curl http://localhost:8000/metadata
```

## 📝 License

This project is part of the MLOps course and follows the same licensing terms.

## 🤝 Contributing

Contributions are welcome! Please follow the existing code style and add appropriate tests for new features.

## 📞 Support

For issues or questions, please refer to the main project documentation or contact the development team.
