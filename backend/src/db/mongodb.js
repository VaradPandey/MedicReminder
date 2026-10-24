import mongoose from "mongoose";

const connectDb = async () => {
    try {
        const localURI = 'mongodb://localhost:27017/medicreminder';
        const mongoURI = process.env.MONGO_URI_ATLAS || process.env.MONGO_URI || localURI;
        const connectionInstance = await mongoose.connect(mongoURI);
        console.log(`MongoDB connected: ${connectionInstance.connection.host}`);
        return connectionInstance;
    } catch (err) {
        console.error("MongoDB connection error:", err.message);
        throw err;
    }
}

export { connectDb };