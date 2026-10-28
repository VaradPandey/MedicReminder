import mongoose from "mongoose";

const connectDb = async () => {
    try {
        let mongoURI = process.env.MONGO_URI_ATLAS || process.env.MONGO_URI;
        if (!mongoURI) {
            if (process.env.NODE_ENV === "production") {
                throw new Error("Missing required MONGO_URI_ATLAS or MONGO_URI environment variable in production.");
            }
            mongoURI = 'mongodb://localhost:27017/medicreminder';
        }
        const connectionInstance = await mongoose.connect(mongoURI);
        console.log(`MongoDB connected: ${connectionInstance.connection.host}`);
        return connectionInstance;
    } catch (err) {
        console.error("MongoDB connection error:", err.message);
        throw err;
    }
}

export { connectDb };