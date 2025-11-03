import mongoose from "mongoose";

const connectDb=async()=>{
    try{
        const connectionInstance=await mongoose.connect('mongodb://localhost:27017/sankalp');
        console.log(`MongoDB connected: ${connectionInstance.connection.host}`);
    }catch(err){
        console.log("MongoDB connection error:",err);
        process.exit(1);
    }
}

export {connectDb};